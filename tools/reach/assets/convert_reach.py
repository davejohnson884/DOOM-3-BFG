"""Convert a private ReachAssetExport bundle to BFG MD5 assets.

RMF reader: Gravemind2401/Reclaimer, pinned 36224d7 (GPL-3.0).
Animation layout/codec reference: TheGuardians/TagTool ce2dc6a (GPL-3.0),
XboxChaos/Assembly fd14ef3. Codec 1/3 only; reject every other format.
No game assets or proprietary scripts are embedded in this program.
"""
import argparse
import base64
import hashlib
import io
import json
import math
import re
import struct
import tempfile
import uuid
import wave
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from rmf_reader.SceneReader import SceneReader

SCALE = 120.0  # 3048 millimetres/Halo unit / 25.4 mm per BFG inch


def raw(record):
    return base64.b64decode(record['raw'], validate=True)


def name(record):
    return next(f['text'] for f in record['fields'] if f['name'] == 'Name')


def slug(text):
    return re.sub('[^a-zA-Z0-9_-]', '_', text).strip('_')


def qnormalize(q):
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    if not np.isfinite(q).all() or (norm < 0.5).any():
        raise ValueError('Invalid source quaternion')
    return q / norm


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack((aw*bx+ax*bw+ay*bz-az*by,
                     aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw,
                     aw*bw-ax*bx-ay*by-az*bz), axis=-1)


def qmatrix(q):
    x, y, z, w = np.moveaxis(qnormalize(q), -1, 0)
    result = np.zeros(q.shape[:-1] + (4, 4))
    result[..., 0, 0] = 1-2*(y*y+z*z)
    result[..., 0, 1] = 2*(x*y-z*w)
    result[..., 0, 2] = 2*(x*z+y*w)
    result[..., 1, 0] = 2*(x*y+z*w)
    result[..., 1, 1] = 1-2*(x*x+z*z)
    result[..., 1, 2] = 2*(y*z-x*w)
    result[..., 2, 0] = 2*(x*z-y*w)
    result[..., 2, 1] = 2*(y*z+x*w)
    result[..., 2, 2] = 1-2*(x*x+y*y)
    result[..., 3, 3] = 1
    return result


def matrixq(matrix):
    """Quaternion for a conventional column-vector rotation matrix."""
    m = np.asarray(matrix)[:3, :3]
    if not np.allclose(m.T @ m, np.eye(3), atol=0.0002) or np.linalg.det(m) < 0.99:
        raise ValueError('Non-rigid bind transform')
    if np.trace(m) > 0:
        s = math.sqrt(np.trace(m)+1)*2
        q = [(m[2, 1]-m[1, 2])/s, (m[0, 2]-m[2, 0])/s, (m[1, 0]-m[0, 1])/s, s/4]
    else:
        i = int(np.argmax(np.diag(m))); j = (i+1) % 3; k = (i+2) % 3
        s = math.sqrt(1+m[i, i]-m[j, j]-m[k, k])*2
        q = [0., 0., 0., (m[k, j]-m[j, k])/s]
        q[i] = s/4; q[j] = (m[j, i]+m[i, j])/s; q[k] = (m[k, i]+m[i, k])/s
    return qnormalize(q)


def md5q(q):
    # idQuat::ToMat3 stores axes as columns, opposite System.Numerics.
    q = np.array(q, copy=True); q[..., :3] *= -1
    # BFG CalcW/ToQuat reconstructs POSITIVE W (different from legacy MD5 importers).
    q[q[..., 3] < 0] *= -1
    return q[..., :3]


def world_matrices(q, t, parents):
    result = qmatrix(q)
    result[..., :3, 3] = t
    for i, parent in enumerate(parents):
        if parent >= i or parent < -1:
            raise ValueError('Invalid/cyclic skeleton order')
        if parent >= 0:
            result[..., i, :, :] = result[..., parent, :, :] @ result[..., i, :, :]
    return result


def read_codec(data, start, frame_count, expected):
    codec, nr, nt, ns, error, rate = struct.unpack_from('<4B2f', data, start)
    if codec != expected:
        raise ValueError(f'Unsupported animation codec {codec}, expected {expected}')
    _, _, rb, tb, sb = struct.unpack_from('<5I', data, start+12)
    count = 1 if codec == 1 else frame_count
    rotation_start = start+32
    translation_start = rotation_start+(nr*8 if codec == 1 else nr*rb)
    scale_start = translation_start+(nt*12 if codec == 1 else nt*tb)
    end = scale_start+(ns*4 if codec == 1 else ns*sb)
    if end > len(data) or (codec == 3 and (rb != frame_count*8 or tb != frame_count*12 or sb != frame_count*4)):
        raise ValueError('Invalid codec strides or truncated frames')
    rotations = np.frombuffer(data, '<i2', nr*count*4, rotation_start).reshape(nr, count, 4).astype(float)/32767
    if nr: rotations = qnormalize(rotations)
    translations = np.frombuffer(data, '<f4', nt*count*3, translation_start).reshape(nt, count, 3).astype(float)
    scales = np.frombuffer(data, '<f4', ns*count, scale_start).reshape(ns, count).astype(float)
    return [rotations, translations, scales], end, {'codec': codec, 'error': error, 'playbackRateField': rate}


def flags(data, offset, size, count):
    if not size: return np.zeros((3, count), dtype=bool)
    words = (count+31)//32
    if size != words*12 or offset+size > len(data):
        raise ValueError('Invalid node flag mask size')
    bits = np.unpackbits(np.frombuffer(data, np.uint8, size, offset).reshape(3, words*4), bitorder='little', axis=1)
    return bits[:, :count].astype(bool)


def decode_graph(graph_dir, default_q, default_t):
    graph = json.loads((graph_dir/'graph-raw.json').read_text())
    groups = {}
    for d in sorted((graph_dir/'animation-resources').iterdir()):
        definition = (d/'definition.bin').read_bytes()
        blob = (d/'frames.bin').read_bytes()
        fix = json.loads((d/'fixups.json').read_text())
        count = struct.unpack_from('<i', definition, len(definition)-12)[0]
        if len(definition) != count*100+12: raise ValueError('Unexpected Reach resource definition layout')
        members = []
        for i in range(count):
            start = i*100
            fc, nc, move = struct.unpack_from('<hBB', definition, start+8)
            sizes = struct.unpack_from('<17i', definition, start+12)
            length = struct.unpack_from('<i', definition, start+80)[0]
            offset = next(f['MaskedOffset'] for f in fix['resourceFixups'] if f['Unknown'] == start+92)
            if fc < 1 or nc != len(default_q) or move != 0 or offset < 0 or length < 32 or offset+length > len(blob):
                raise ValueError('Invalid or unsupported animation resource member')
            members.append((fc, nc, sizes, blob[offset:offset+length]))
        groups[int(d.name)] = members
    clips = {}
    for index, record in enumerate(graph['children']['Animations']['elements']):
        entry = record['children']['Shared Animation Data']['elements'][0]
        metadata = raw(entry); group, member = struct.unpack_from('<hh', metadata, 32)
        fc, nc, sizes, data = groups[group][member]
        if struct.unpack_from('<h', metadata, 2)[0] != fc or metadata[0] != nc:
            raise ValueError('Graph/resource frame or node count mismatch')
        static_size, compressed_size, static_flag_size, animated_flag_size, movement_size = sizes[:5]
        if movement_size: raise ValueError('Root motion not supported in this first-person converter')
        static = [np.empty((0, 1, 4)), np.empty((0, 1, 3)), np.empty((0, 1))]
        if static_size:
            static, end, _ = read_codec(data, 0, fc, 1)
            if end > static_size: raise ValueError('Static codec overruns its section')
        animated, end, codec_info = read_codec(data, static_size, fc, 3)
        if end != static_size+compressed_size: raise ValueError('Compressed codec size mismatch')
        sf = flags(data, end, static_flag_size, nc)
        af = flags(data, end+static_flag_size, animated_flag_size, nc)
        if (sf & af).any(): raise ValueError('Conflicting static/animated flags')
        values = [np.tile(default_q, (fc, 1, 1)), np.tile(default_t, (fc, 1, 1)), np.ones((fc, nc))]
        for component in range(3):
            si = ai = 0
            for node in range(nc):
                if sf[component, node]: values[component][:, node] = static[component][si, 0]; si += int(sf[component, node])
                elif af[component, node]: values[component][:, node] = animated[component][ai]; ai += 1
            if si != len(static[component]) or ai != len(animated[component]):
                raise ValueError('Codec channel counts disagree with node masks')
        if not all(np.isfinite(v).all() for v in values) or not np.allclose(values[2], 1, atol=0.0001):
            raise ValueError('Nonfinite or scaled joint animation cannot be represented by MD5')
        events = [{'type': struct.unpack_from('<h', raw(e))[0], 'frame': struct.unpack_from('<h', raw(e), 2)[0]}
                  for e in entry['children']['Frame Events']['elements']]
        clips[name(record)] = {'q': values[0], 't': values[1], 'animated': af,
                              'type': metadata[4], 'frames': fc, 'events': events, 'index': index, 'codec': codec_info}
    idle = clips['first_person:idle']
    for clip in clips.values():
        if clip['type'] == 2:
            # Actual overlay deltas, applied to the actual idle frame; retain original frame count.
            mask = clip['animated'][0]
            clip['q'][:, ~mask] = idle['q'][0, ~mask]
            clip['q'][:, mask] = qmul(idle['q'][0, mask], clip['q'][:, mask])
            mask = clip['animated'][1]
            clip['t'][:, ~mask] = idle['t'][0, ~mask]
            clip['t'][:, mask] += idle['t'][0, mask]
        elif clip['type'] not in (0, 1): raise ValueError('Unsupported replacement animation')
        clip['q'] = qnormalize(clip['q'])
    return clips


def rig(graph, arm_model, gun_model):
    nodes = graph['children']['Skeleton Nodes']['elements']
    names = [name(n) for n in nodes]
    parents = [struct.unpack_from('<h', raw(n), 8)[0] for n in nodes]
    if len(set(names)) != len(names) or parents[0] != -1: raise ValueError('Invalid source skeleton names/root')
    lookup = {b.name: b for m in [arm_model, gun_model] for b in m.bones}
    q = np.array([matrixq(np.array(lookup[n].transform).T) for n in names])
    t = np.array([np.array(lookup[n].transform)[3, :3] for n in names])
    return names, parents, q, t


def fmt(numbers):
    return ' '.join(f'{float(n):.9g}' for n in np.ravel(numbers))


def convert_meshes(scene, model, mesh_indices, joint_names):
    source_world = []
    for b in model.bones:
        local = np.array(b.transform).T
        source_world.append(local if b.parent_index < 0 else source_world[b.parent_index] @ local)
    inverse = np.linalg.inv(np.array(source_world))
    mapping = [joint_names.index(b.name) for b in model.bones]
    surfaces = []
    for mesh_index in mesh_indices:
        mesh = model.meshes[mesh_index]
        vb = scene.vertex_buffer_pool[mesh.vertex_buffer_index]
        ib = scene.index_buffer_pool[mesh.index_buffer_index]
        positions = np.array([list(x)[:3]+[1] for x in vb.position_channels[0]]) @ np.array(mesh.vertex_transform)
        uv = np.array([list(x)[:2]+[0, 1] for x in vb.texcoord_channels[0]]) @ np.array(mesh.texture_transform)
        # Halo and MD5 both use top-origin V; Blender importers invert both.
        uv = uv[:, :2]
        pairs = list(vb.enumerate_blendpairs(mesh.flags)) if vb.blendindex_channels else [(i, [mesh.bone_index], [1.]) for i in range(vb.count)]
        for segment in mesh.segments:
            triangles = list(ib.get_triangles(segment))
            if not triangles: continue
            used = sorted(set(i for tri in triangles for i in tri)); remap = {v: i for i, v in enumerate(used)}
            weights = []; vertices = []
            for i in used:
                _, indices, amounts = pairs[i]
                if not indices or len(indices) > 4 or not np.isclose(sum(amounts), 1): raise ValueError('Unsupported skin influences')
                first = len(weights)
                for bone, amount in zip(indices, amounts):
                    if bone < 0 or bone >= len(mapping): raise ValueError('Invalid vertex joint index')
                    offset = (inverse[bone] @ positions[i])[:3]*SCALE
                    weights.append((mapping[bone], float(amount), offset))
                vertices.append((uv[i], first, len(weights)-first))
            surfaces.append({'material': scene.material_pool[segment.material_index].name,
                             'verts': vertices, 'weights': weights,
                             'tris': [(remap[a], remap[b], remap[c]) for a, b, c in triangles]})
    return surfaces


def skin(surfaces, world):
    result = []
    for surface in surfaces:
        if '_skin' not in surface:
            surface['_skin'] = (np.array([j for j, _, _ in surface['weights']]),
                                np.array([a for _, a, _ in surface['weights']]),
                                np.array([o for _, _, o in surface['weights']]),
                                np.array([first for _, first, _ in surface['verts']]))
        joints, amounts, offsets, starts = surface['_skin']
        wp = np.einsum('wij,wj->wi', world[joints, :3, :3], offsets)+world[joints, :3, 3]*SCALE
        result.append(np.add.reduceat(wp*amounts[:, None], starts))
    return result


def write_mesh(path, names, parents, q, t, surfaces):
    world = world_matrices(q, t, parents)
    lines = ['MD5Version 10', 'commandline "Reach owned-data conversion"', f'numJoints {len(names)}', f'numMeshes {len(surfaces)}', 'joints {']
    for i, (n, p) in enumerate(zip(names, parents)):
        lines.append(f'  "{n}" {p} ( {fmt(world[i, :3, 3]*SCALE)} ) ( {fmt(md5q(matrixq(world[i])))} )')
    lines.append('}')
    for surface in surfaces:
        lines.extend(['mesh {', f'  shader "reach/{slug(surface["material"])}"', f'  numverts {len(surface["verts"])}'])
        for i, (uv, first, count) in enumerate(surface['verts']): lines.append(f'  vert {i} ( {fmt(uv)} ) {first} {count}')
        lines.append(f'  numtris {len(surface["tris"])}')
        # Reach's indices use the opposite front-face winding from idTech.
        for i, (a, b, c) in enumerate(surface['tris']): lines.append(f'  tri {i} {a} {c} {b}')
        lines.append(f'  numweights {len(surface["weights"])}')
        for i, (joint, amount, offset) in enumerate(surface['weights']): lines.append(f'  weight {i} {joint} {amount:.9g} ( {fmt(offset)} )')
        lines.append('}')
    path.write_text('\n'.join(lines)+'\n')


def write_anim(path, names, parents, clip, surfaces):
    q, t = clip['q'], clip['t']; fc = len(q)
    lines = ['MD5Version 10', 'commandline "Reach codec 1/3 original frames"', f'numFrames {fc}', f'numJoints {len(names)}', 'frameRate 30', f'numAnimatedComponents {len(names)*6}', 'hierarchy {']
    for i, (n, p) in enumerate(zip(names, parents)): lines.append(f'  "{n}" {p} 63 {i*6}')
    lines.append('}'); lines.append('bounds {')
    world = world_matrices(q, t, parents)
    for frame in world:
        points = np.concatenate(skin(surfaces, frame))
        lines.append(f'  ( {fmt(points.min(axis=0)-0.1)} ) ( {fmt(points.max(axis=0)+0.1)} )')
    lines.extend(['}', 'baseframe {'])
    for i in range(len(names)): lines.append(f'  ( {fmt(t[0, i]*SCALE)} ) ( {fmt(md5q(q[0, i]))} )')
    lines.append('}')
    for frame in range(fc):
        lines.append(f'frame {frame} {{')
        for i in range(len(names)): lines.append('  '+fmt(t[frame, i]*SCALE)+' '+fmt(md5q(q[frame, i])))
        lines.append('}')
    path.write_text('\n'.join(lines)+'\n')


def materials(scenes, bundle, output, used):
    lines = []; converted = {}; descriptions = {}
    directory = output/'textures/reach'; directory.mkdir(parents=True)
    for scene in scenes:
        for material in scene.material_pool:
            if material.name not in used or material.name in descriptions: continue
            descriptions[material.name] = material
            maps = {}
            for usage in ['diffuse', 'normal', 'specular', 'self_illum']:
                mapping = next((m for m in material.texture_mappings if m.texture_usage == usage), None)
                if mapping is None: continue
                texture = scene.texture_pool[mapping.texture_index]
                source = next(bundle.rglob(slug(texture.name)+'.dds'), None)
                if source is None: raise ValueError(f'Missing required texture: {texture.name}')
                identifier = slug(texture.name)+'_'+usage
                if identifier not in converted:
                    image = read_dds(source)
                    pixels = np.array(image)
                    if usage == 'specular':
                        pixels[..., :3] = pixels[..., 3, None]; pixels[..., 3] = 255
                    elif usage == 'normal':
                        # Reclaimer supplies an ordinary BC5 RG DDS; reconstruct tangent normal Z.
                        xy = pixels[..., :2].astype(float)/127.5-1
                        pixels[..., 2] = np.clip((np.sqrt(np.maximum(0, 1-(xy*xy).sum(axis=-1)))+1)*127.5, 0, 255).astype(np.uint8)
                        pixels[..., 3] = 255
                    elif material.alpha_mode == 'opaque': pixels[..., 3] = 255
                    Image.fromarray(pixels).save(directory/(identifier+'.tga'))
                    converted[identifier] = {'source': texture.name, 'usage': usage, 'size': list(image.size)}
                maps[usage] = 'textures/reach/'+identifier+'.tga'
            lines.extend(['reach/'+slug(material.name), '{'])
            if material.alpha_mode != 'opaque':
                lines.extend(['  twoSided', '  translucent', '  noShadows'])
                if 'diffuse' in maps: lines.extend(['  {', '    blend blend', '    map '+maps['diffuse'], '  }'])
            else:
                if 'normal' in maps: lines.append('  bumpmap '+maps['normal'])
                if 'diffuse' in maps: lines.append('  diffusemap '+maps['diffuse'])
                if 'specular' in maps: lines.append('  specularmap '+maps['specular'])
            if 'self_illum' in maps: lines.extend(['  {', '    blend add', '    map '+maps['self_illum'], '  }'])
            lines.append('}')
    if used-set(descriptions): raise ValueError('Missing material declarations')
    (output/'materials').mkdir(); (output/'materials/reach_ar.mtr').write_text('\n'.join(lines)+'\n')
    return converted


def read_dds(source):
    data = source.read_bytes()
    if data[84:88] == b'XBOX':
        # Reclaimer uses an extended header for Reach signed DXN normals.
        # MCC payload is linear BC5 SNORM; replace only the container header.
        xbox_format = struct.unpack_from('<I', data, 128)[0]
        tile_mode = struct.unpack_from('<I', data, 148)[0]
        if xbox_format not in (4, 6) or tile_mode not in (0, 1):
            raise ValueError(f'Unsupported extended DDS format/tile mode: {xbox_format}/{tile_mode}')
        header = bytearray(data[:128]); header[84:88] = b'DX10'
        data = bytes(header)+struct.pack('<5I', 83 if xbox_format == 4 else 84, 3, 0, 1, 1)+data[164:]
    if data[84:88] == b'DX10':
        format_code = struct.unpack_from('<I', data, 128)[0]
        height, width = struct.unpack_from('<II', data, 12)
        if format_code == 87:
            return Image.frombytes('RGBA', (width, height), data[148:148+width*height*4], 'raw', 'BGRA')
        if format_code == 65:
            pixels = np.zeros((height, width, 4), dtype=np.uint8)
            pixels[..., 3] = np.frombuffer(data, np.uint8, width*height, 148).reshape(height, width)
            return Image.fromarray(pixels)
    return Image.open(io.BytesIO(data)).convert('RGBA')


def sounds(bundle, output):
    directory = output/'sound/reach'; directory.mkdir(parents=True)
    records = []
    for file in sorted((bundle/'sounds').glob('*.wav')):
        data = file.read_bytes(); code, channels, rate = struct.unpack_from('<HHI', data, 20)
        bits = struct.unpack_from('<H', data, 34)[0]; size = struct.unpack_from('<I', data, 40)[0]
        if data[:4] != b'RIFF' or data[36:40] != b'data' or size+44 > len(data): raise ValueError('Invalid collected WAVE')
        if code != 3 or bits != 32 or channels < 1 or channels > 8: raise ValueError('Unexpected source PCM format')
        source = np.frombuffer(data, '<f4', size//4, 44).reshape(-1, channels)
        if not np.isfinite(source).all(): raise ValueError('Nonfinite PCM data')
        source = source.mean(axis=1)
        # BFG accepts 11025/22050/44100 Hz PCM16. Donor samples are normally 48kHz.
        count = round(len(source)*44100/rate)
        converted = np.interp(np.arange(count)*rate/44100, np.arange(len(source)), source)
        pcm = np.rint(np.clip(converted, -1, 1)*32767).astype('<i2')
        target = directory/file.name
        with wave.open(str(target), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(pcm.tobytes())
        records.append({'file': 'sound/reach/'+file.name, 'seconds': len(pcm)/44100})
    return records


def convert(bundle, output):
    bundle = Path(bundle); output = Path(output)
    if output.exists(): raise ValueError('Use a new output directory; existing assets will not be overwritten')
    manifest = json.loads((bundle/'manifest.json').read_text())
    gun_path = bundle/next(x['file'] for x in manifest['exports'] if x['kind'] == 'skinned-model' and x['tag'] == manifest['firstPersonModel'])
    arm_path = bundle/next(x['file'] for x in manifest['exports'] if x['kind'] == 'skinned-model' and x['tag'] in manifest['armCandidates'])
    arm_scene = SceneReader.open_scene(str(arm_path)); gun_scene = SceneReader.open_scene(str(gun_path))
    arms = arm_scene.model_pool[0]; gun = gun_scene.model_pool[0]
    if arm_scene.unit_scale != 3048 or gun_scene.unit_scale != 3048: raise ValueError('Unexpected RMF unit scale')
    graph_dir = next((bundle/'animation-graphs').iterdir()); graph = json.loads((graph_dir/'graph-raw.json').read_text())
    names, parents, default_q, default_t = rig(graph, arms, gun)
    clips = decode_graph(graph_dir, default_q, default_t)
    surfaces = convert_meshes(arm_scene, arms, [next(p.mesh_index for r in arms.regions if r.name == 'arms' for p in r.permutations if p.name == 'default')], names)
    surfaces += convert_meshes(gun_scene, gun, [0], names)
    source_joint_count = len(names)
    # Native BFG weapon code expects these marker joints by name.
    for joint, marker_name in [('barrel', 'primary_trigger'), ('flash', 'primary_trigger'), ('eject', 'primary_ejection'), ('guiLight', 'fx_display_light')]:
        marker = next(m for m in gun.markers if m.name == marker_name).instances[0]
        names.append(joint); parents.append(names.index(gun.bones[marker.bone_index].name))
        for clip in clips.values():
            count = clip['frames']
            clip['q'] = np.concatenate([clip['q'], np.tile(qnormalize(marker.rotation), (count, 1, 1))], axis=1)
            clip['t'] = np.concatenate([clip['t'], np.tile(marker.position, (count, 1, 1))], axis=1)
    names[0] = 'origin'
    mesh_dir = output/'models/md5/weapons/reach_ar'; mesh_dir.mkdir(parents=True)
    idle = clips['first_person:idle']
    write_mesh(mesh_dir/'view.md5mesh', names, parents, idle['q'][0], idle['t'][0], surfaces)
    animation_info = {}
    for label, clip in clips.items():
        short = slug(label.removeprefix('first_person:'))
        print('Converting original animation:', short, clip['frames'], 'frames', flush=True)
        write_anim(mesh_dir/(short+'.md5anim'), names, parents, clip, surfaces)
        animation_info[short] = {k: v for k, v in clip.items() if k not in ['q', 't', 'animated']}
    textures = materials([arm_scene, gun_scene], bundle, output, set(s['material'] for s in surfaces))
    audio = sounds(bundle, output)
    report = {'sourceBuild': manifest['BuildString'], 'sourceJoints': source_joint_count, 'md5Joints': len(names),
              'surfaces': len(surfaces), 'vertices': sum(len(s['verts']) for s in surfaces),
              'triangles': sum(len(s['tris']) for s in surfaces), 'animations': animation_info,
              'textures': textures, 'sounds': audio, 'mmPerHaloUnit': 3048, 'bfgUnitsPerHaloUnit': SCALE,
              'frameRate': 30, 'frameRateBasis': 'Blam nominal animation sampling; runtime playback parity not yet verified',
              'limitations': ['Halo material lighting and detail layers are approximated by BFG diffuse/normal/specular shaders.',
                              'Armor color-change masks, ammo display/compass and gameplay wiring require follow-up.',
                              'Original source frame counts preserved; additive screens composed against actual idle frame. In-game acceptance is pending.']}
    (output/'conversion-report.json').write_text(json.dumps(report, indent=2)+'\n')
    from check_md5 import check
    check(output, {slug(label.removeprefix('first_person:')): world_matrices(clip['q'], clip['t'], parents) for label, clip in clips.items()})
    print('Converted assets:', output)
    return names, parents, clips, surfaces, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--bfg', type=Path)
    args = parser.parse_args()
    output = args.out or Path.cwd()/('reach-weapon-data-'+uuid.uuid4().hex)
    if args.bfg and output.resolve().is_relative_to(args.bfg.resolve()):
        raise ValueError('Output must be outside the BFG install')
    def run(bundle):
        convert(bundle, output)
        if args.bfg:
            from build_weapon import build, resource_file
            build(bundle, output, resource_file(args.bfg, 'def/weapon_machinegun.def'))
            (Path.cwd()/'reach-weapon-data.path').write_text(str(output.resolve()))
    if args.donor.is_dir(): run(args.donor)
    else:
        with tempfile.TemporaryDirectory(prefix='reach-donor-') as temp:
            with zipfile.ZipFile(args.donor) as archive:
                if sum(i.file_size for i in archive.infolist()) > 1024**3: raise ValueError('Donor ZIP exceeds extraction limit')
                for item in archive.infolist():
                    path = Path(item.filename.replace('\\', '/'))
                    if path.is_absolute() or '..' in path.parts or ':' in item.filename: raise ValueError('Unsafe donor ZIP path')
                archive.extractall(temp)
            run(Path(temp))
    print('Weapon assets prepared. Run Start-Reach-rifle.cmd from the matching source-build package.')


if __name__ == '__main__':
    main()
