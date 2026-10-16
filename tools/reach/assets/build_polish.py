"""Asset-only r16 polish for the owner's working r15 Reach installation.

Read private donor exports locally. Re-evaluate the original material maps at
1x/2x resolution; this is not AI super-resolution. RMAO values are authored
RBDoom approximations, not recovered Blam roughness/metalness parameters.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import uuid
import zipfile

import numpy as np
from PIL import Image
from build_appearance import combine_normals, extract, normal, rgba_tga, tiled
from build_effects import bake_palette, bitmap, stage, sprite_material
from convert_reach import read_dds, slug
from rmf_reader.SceneReader import SceneReader

PACK = 'zzzzzzzzzzzz_reach_polish_r16.pk4'
REPAIR = 'zzzzzzzzzzz_reach_repair_r15.pk4'
MATERIAL_FILE = 'materials/reach_repair15.mtr'
PARTICLES = ('reach_ar_flash_r15', 'reach_frag_explosion_r15')
# (base roughness, metalness). Deliberate host-material authoring controls.
SURFACES = {
    'spartan_fp_armor': (.48, 0.), 'spartan_fp_glove': (.78, 0.),
    'spartan_rubber_suit': (.86, 0.), 'spartan_armor': (.48, 0.),
    'spartan_forearm_tricorder': (.48, 0.),
    'assault_rifle_composite': (.55, 0.), 'assault_rifle_metal': (.34, .65),
    'assault_rifle_metal_shiny': (.24, .85), 'assault_rifle_rubber': (.82, 0.),
}


def read_palette(path):
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != {'profile-colors.bin', 'profile-colors.json'}:
            raise ValueError('Choose the collected reach-palette ZIP')
        if sum(x.file_size for x in archive.infolist()) > 65536 or archive.testzip():
            raise ValueError('Invalid palette ZIP')
        raw = archive.read('profile-colors.bin')
        doc = json.loads(archive.read('profile-colors.json'))
    if (doc.get('schemaVersion') != 1 or doc.get('schema') != 'ReachMCC/matg.xml'
            or doc.get('tableOffset') != 0x498 or doc.get('ElementSize') != 12
            or doc.get('Count') != 30 or len(raw) != 360
            or hashlib.sha256(raw).hexdigest() != doc.get('rawSha256', '').lower()):
        raise ValueError('Palette does not match the collected MCC Reach layout')
    colors = np.array(list(struct.iter_unpack('<fff', raw)))
    if not np.isfinite(colors).all() or np.any(colors < 0) or np.any(colors > 1):
        raise ValueError('Invalid source colors')
    if len(doc['profileColors']) != 30: raise ValueError('Palette JSON entry count differs')
    for i, row in enumerate(doc['profileColors']):
        if row['index'] != i or struct.pack('<fff', *row['rgb']) != raw[i*12:(i+1)*12]:
            raise ValueError('Palette JSON differs from raw source data')
    # The owner's selected Steel/Steel target uses the darkest of the three
    # neutral entries. The raw table itself does not contain color-name labels.
    if not (np.all(colors[:3] == colors[:3, :1]) and np.all(np.diff(colors[:3, 0]) > 0)):
        raise ValueError('Expected the three ordered neutral palette entries')
    return colors[0], {'sourceBuild': doc['BuildString'], 'rawSha256': doc['rawSha256'],
                       'sourceIndex': 0, 'selection': 'Steel / Steel, owner requested',
                       'indexBasis': 'darkest of the first three neutral entries; source table has no labels'}


def to_linear(value):
    return np.where(value <= .04045, value/12.92, ((value+.055)/1.055)**2.4)


def to_srgb(value):
    value = np.maximum(value, 0)
    return np.where(value <= .0031308, value*12.92, 1.055*value**(1/2.4)-.055)


def armor_multiplier(mask, steel):
    # Source two-change-color shader: independent R/G multiplicative blends.
    # Blue is not a third armor-color channel in this material option.
    return ((1-mask[..., 0, None])+mask[..., 0, None]*steel) * \
           ((1-mask[..., 1, None])+mask[..., 1, None]*steel)


def material_block(text, name):
    pattern = r'(?<![\w/])'+re.escape(name)+r'\s*\{(?:[^{}]|\{[^{}]*\})*\}'
    match = re.search(pattern, text)
    if match is None: raise ValueError('Missing installed material: '+name)
    return match


def bake_material(scene, mat, bundle, entries, steel, scale, lighting):
    maps = {m.texture_usage: m for m in mat.texture_mappings}
    def image(usage):
        name = scene.texture_pool[maps[usage].texture_index].name
        source = next(bundle.rglob(slug(name)+'.dds'), None)
        if source is None: raise ValueError('Missing donor map: '+name)
        return read_dds(source)
    source_size = image('diffuse').size
    size = tuple(v*scale for v in source_size)
    if max(size) > 4096: raise ValueError('Material bake exceeds 4096 pixels')
    def sample(usage): return tiled(image(usage), size, maps[usage].tiling)
    diffuse = to_linear(sample('diffuse')[..., :3])
    if 'color_change' in maps:
        diffuse *= armor_multiplier(sample('color_change'), steel)
    if 'diffuse_detail' in maps:
        # Neutral-centered detail response; preserve donor tiling and evaluate
        # at the destination footprint instead of enlarging the old flat bake.
        detail = to_linear(sample('diffuse_detail')[..., :3])/to_linear(np.array(.5))
        diffuse *= .6+.4*detail
    tints = {t.tint_usage: np.array(t.tint_color[:3])/255 for t in mat.tints}
    diffuse *= to_linear(tints.get('albedo', np.ones(3)))
    normals = normal(sample('normal'))
    if 'normal_detail' in maps:
        normals = combine_normals(normals, normal(sample('normal_detail')))
    source_spec = sample('specular')
    if int(maps['specular'].channel_mask) == 8:
        source_spec = np.repeat(source_spec[..., 3, None], 3, axis=-1)
    else: source_spec = source_spec[..., :3]
    spec = source_spec*tints.get('specular', 1)
    roughness, metalness = SURFACES[mat.name]
    # Source specular amplitude supplies a spatial highlight mask, not an
    # assertion that Reach stored this derived roughness map.
    rough = np.clip(roughness+(.5-source_spec.mean(axis=-1))*.2, .12, .95)
    rmao = np.dstack([rough, np.full_like(rough, metalness), np.ones_like(rough),
                     np.full_like(rough, .5)])  # neutral height, matching host convention
    prefix = f'textures/reach/polish16_{lighting}_{scale}x/{mat.name}'
    outputs = {'diffuse': to_srgb(diffuse), 'normal': normals*.5+.5}
    outputs['rmao' if lighting == 'pbr' else 'specular'] = rmao if lighting == 'pbr' else spec
    for role, pixels in outputs.items(): entries[prefix+'_'+role+'.tga'] = rgba_tga(pixels)
    body = 'reach/repair15/'+mat.name+'\n{\n    bumpmap '+prefix+'_normal.tga\n    diffusemap '+prefix+'_diffuse.tga\n'
    role = 'rmao' if lighting == 'pbr' else 'specular'
    body += ('    rmaomap ' if lighting == 'pbr' else '    specularmap ')+prefix+'_'+role+'.tga\n'
    if 'self_illum' in maps:
        # Keep the actual blue source tint and emission mask separate from Steel.
        illum = sample('self_illum')[..., :3]*tints.get('self_illum', 1)
        entries[prefix+'_illum.tga'] = rgba_tga(illum)
        body += '    {\n        blend add\n        map '+prefix+'_illum.tga\n    }\n'
    body += '}\n'
    return body, {'sourceSize': source_size, 'bakeSize': size,
                  'detailTiling': {k: list(v.tiling) for k, v in maps.items() if k.endswith('detail')},
                  'authoredRoughness': roughness, 'authoredMetalness': metalness,
                  'emissiveTintRGBA8': next((list(t.tint_color) for t in mat.tints if t.tint_usage == 'self_illum'), None)}


def padded_atlas(pixels, count, gutter=4):
    """Isolate tiles and end in black: BFG crossfades to the following tile."""
    if pixels.shape[1] % count: raise ValueError('Invalid sprite strip width')
    tiles = [np.pad(t, ((gutter, gutter), (gutter, gutter), (0, 0)))
             for t in np.split(pixels, count, axis=1)]
    total = 1 << count.bit_length()  # strictly greater, including powers of two
    tiles.extend(np.zeros_like(tiles[0]) for _ in range(total-count))
    return np.concatenate(tiles, axis=1), total


def bake_effects(bundle, entries, materials):
    base = 'objects\\weapons\\rifle\\assault_rifle\\fx\\particles\\'
    fire = 'fx\\bitmaps\\weapon_fire\\'
    specs = [
        ('ar_round', base+'muzzle_flash_round', fire+'muzzle_flash_round_gaseous', fire+'gradients\\muzzle_flare_assault_rifle', (248, 248), (0.,)),
        ('ar_long', base+'muzzle_flash_long', fire+'muzzle_flash_long_gaseous', fire+'gradients\\muzzle_flare_assault_rifle_long', (120, 504), (0.,)),
        ('frag_fireball', 'objects\\weapons\\grenade\\frag_grenade\\fx\\particles\\fireball', 'fx\\bitmaps\\atmospheric_rolling\\fireball_plate', 'fx\\particles\\_gradients\\fireball_human', (120, 120), (0., .33, .66, 1.)),
    ]
    frames = {}
    for name, particle, texture, palette, size, ages in specs:
        pixels, count = bake_palette(bundle, particle, texture, palette, size, ages)
        pixels, frames[name] = padded_atlas(pixels, count)
        path = 'textures/reach/effects16/'+name+'.tga'
        entries[path] = rgba_tga(pixels)
        # Source fireball uses alpha blend. Our RGB is already premultiplied;
        # ONE / ONE_MINUS_SRC_ALPHA preserves that coverage without squaring it.
        blend = 'gl_one, gl_one_minus_src_alpha' if name == 'frag_fireball' else 'add'
        body = sprite_material('reach/effects15/'+name, path, blend)
        if name.startswith('ar_'):
            body = body.replace('        vertexColor', '        rgb 2\n        vertexColor')
        match = material_block(materials, 'reach/effects15/'+name)
        materials = materials[:match.start()]+body+materials[match.end():]
    # Original smoke/blast are already soft cards, not palette-noise fields.
    for name, tag in [('smoke', 'fx\\bitmaps\\atmospheric\\soft_smoke_large'), ('blast', 'fx\\bitmaps\\flash\\flash_soft')]:
        path = 'textures/reach/effects16/'+name+'.tga'
        pixels = bitmap(bundle, tag)
        if name == 'blast': pixels[..., :3] *= pixels[..., 3, None]
        entries[path] = rgba_tga(pixels)
        match = material_block(materials, 'reach/effects15/'+name)
        body = sprite_material('reach/effects15/'+name, path, 'blend' if name == 'smoke' else 'add')
        materials = materials[:match.start()]+body+materials[match.end():]
    # Stock stage size is a half-width. Keep axial cards pointed down +X:
    # POR_Z angle~0 has its long up-axis along X; POR_Y angle270 does likewise.
    flash = stage('reach/effects15/ar_round', .09, '5.5', offset='1.5 0 0', frames=frames['ar_round'], fade=.9)
    flash += stage('reach/effects15/ar_long', .09, '2.8', 3.2, 'z', offset='8 0 0', angle=.001, frames=frames['ar_long'], fade=.9)
    flash += stage('reach/effects15/ar_long', .09, '2.8', 3.2, 'y', offset='8 0 0', angle=270, frames=frames['ar_long'], fade=.9)
    explosion = stage('reach/effects15/blast', .10, '24 to 52', fade=1)
    explosion += stage('reach/effects15/frag_fireball', 1.15, '22 to 64', frames=frames['frag_fireball'], count=3, speed='0 to 30', fade=.8)
    explosion += stage('reach/effects15/smoke', 2.3, '25 to 85', count=5, speed='15 to 40', fade=.8, color='.18 .17 .15 .5', delay=.06)
    for name, body in zip(PARTICLES, [flash, explosion]):
        entries['particles/'+name+'.prt'] = ('particle '+name+'.prt {\n'+body+'}\n').encode()
    return materials, frames


def known_save_path():
    if os.name != 'nt': return None
    import ctypes
    guid = ctypes.create_string_buffer(uuid.UUID('4c5c32ff-bb9d-43b0-b5b4-2d72e54eaaa4').bytes_le)
    pointer = ctypes.c_void_p()
    shell = ctypes.WinDLL('shell32'); ole = ctypes.WinDLL('ole32')
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    if shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(pointer)) != 0:
        return None
    try: return Path(ctypes.wstring_at(pointer))/'id Software'/'RBDOOM 3 BFG'
    finally: ole.CoTaskMemFree(pointer)


def move_particle_caches(game, cache_root=None):
    # In production mode BFG ignores particle source checksums. Invalidate only
    # the two changed derived particle files, preserving each as a backup.
    roots = [Path(game).resolve()]
    saved = Path(cache_root).resolve() if cache_root else known_save_path()
    if saved is not None: roots.append(saved)
    moved = []
    for root in dict.fromkeys(roots):
        for folder in ('reach', 'base'):
            for name in PARTICLES:
                candidate = root/folder/'generated/particles'/(name+'.bprt')
                if not candidate.is_file(): continue
                if candidate.resolve() != candidate.absolute():
                    raise ValueError('Refusing redirected particle cache: '+str(candidate))
                target = candidate.with_name(candidate.name+'.r16-backup-'+uuid.uuid4().hex[:12])
                candidate.rename(target)
                moved.append({'original': str(candidate), 'backup': str(target)})
    return moved


def build(donor, effects, palette, game, scale=2, lighting='pbr', cache_root=None):
    game = Path(game).resolve()
    repair = game/'reach'/REPAIR
    if not repair.is_file(): raise FileNotFoundError('Install and apply the working r15 repair first: '+str(repair))
    steel, palette_report = read_palette(palette)
    manifests = [json.loads((Path(folder)/'manifest.json').read_text()) for folder in (donor, effects)]
    if ([d.get('schemaVersion') for d in manifests] != [1, 2]
            or any(d.get('BuildString') != palette_report['sourceBuild'] for d in manifests)):
        raise ValueError('Original assets, focused effects and palette must come from the same MCC Reach build')
    entries = {}
    with zipfile.ZipFile(repair) as archive:
        if archive.testzip(): raise ValueError('Installed r15 repair failed CRC verification')
        materials = archive.read(MATERIAL_FILE).decode()
    reports = {}
    for path in Path(donor).rglob('*.rmf'):
        scene = SceneReader.open_scene(str(path))
        for mat in scene.material_pool:
            if mat.name not in SURFACES or mat.name in reports or mat.alpha_mode != 'opaque': continue
            print('Baking '+mat.name+' ('+str(scale)+'x, '+lighting+')', flush=True)
            body, report = bake_material(scene, mat, Path(donor), entries, steel, scale, lighting)
            match = material_block(materials, 'reach/repair15/'+mat.name)
            materials = materials[:match.start()]+body+materials[match.end():]
            reports[mat.name] = report
    if set(reports) != set(SURFACES): raise ValueError('Original donor is missing required rifle/arm materials')
    materials, frames = bake_effects(Path(effects), entries, materials)
    entries[MATERIAL_FILE] = materials.encode()
    report = {'revision': 'r16', 'palette': palette_report, 'paletteSourceRGB': steel.tolist(),
              'lights': 'Original blue TACPAD tint and self-illumination mask',
              'resolutionScale': scale, 'lighting': lighting, 'materials': reports, 'spriteFrames': frames,
              'sourceRepairSha256': hashlib.sha256(repair.read_bytes()).hexdigest(),
              'changes': ['independent source R/G armor color masks', 'source billboard alpha on frag fireball',
                          'isolated atlas frames ending in black', 'brighter and wider short muzzle flash',
                          'higher-resolution source-detail bake', 'authored roughness/metalness option'],
              'modelChanged': False, 'animationChanged': False, 'poseChanged': False, 'scriptsChanged': False,
              'executableChanged': False, 'runtimeTest': 'Owner playtest required; no game executed in cloud',
              'limitations': ['Steel uses neutral source entry 0; the table has no name labels.',
                             'Blam material BRDF, particle function curves and HDR are adapted, not identical.',
                             '2x re-evaluates original maps and tiling; it is not AI upscaling or new high-resolution source art.',
                             'PBR roughness/metalness are authored host approximations; use classic to compare.',
                             'Custom fs_savepath needs --cache-root for the two targeted generated particle files.'],
              'files': {n: hashlib.sha256(b).hexdigest() for n, b in entries.items()}}
    entries['reach-polish16-report.json'] = json.dumps(report, indent=2).encode()
    destination = game/'reach'/PACK
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='reach-polish-', suffix='.tmp', delete=False) as handle:
        staged = Path(handle.name)
    try:
        with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()): archive.writestr(name, data)
        with zipfile.ZipFile(staged) as archive:
            if archive.testzip(): raise ValueError('Polish PK4 failed CRC verification')
        report['particleCacheBackups'] = move_particle_caches(game, cache_root)
        if destination.exists():
            destination.rename(destination.with_name(destination.name+'.backup-'+uuid.uuid4().hex[:12]))
        staged.replace(destination)
    finally: staged.unlink(missing_ok=True)
    (game/'reach-polish16-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Installed '+str(destination))
    print('Start Play-Reach-projection.cmd. For V/G use your working r15 controls CFG if needed.')
    return report


def unpack(path, stack):
    path = Path(path)
    if path.is_dir(): return path
    directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='reach-polish-donor-')))
    with zipfile.ZipFile(path) as archive: extract(archive, directory)
    return directory


def choose(title):
    import tkinter as tk
    from tkinter.filedialog import askopenfilename
    root = tk.Tk(); root.withdraw()
    try: name = askopenfilename(title=title, filetypes=[('Reach export ZIP', '*.zip')])
    finally: root.destroy()
    if not name: raise ValueError('No source chosen; no game files changed')
    return Path(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--donor', type=Path)
    parser.add_argument('--effects', type=Path)
    parser.add_argument('--palette', type=Path)
    parser.add_argument('--scale', type=int, choices=(1, 2), default=2)
    parser.add_argument('--lighting', choices=('classic', 'pbr'), default='pbr')
    parser.add_argument('--cache-root', type=Path, help='Optional custom fs_savepath')
    parser.add_argument('--undo', action='store_true')
    args = parser.parse_args()
    if args.undo:
        destination = args.game/'reach'/PACK
        if destination.is_file():
            destination.rename(destination.with_name(destination.name+'.disabled-'+uuid.uuid4().hex[:12]))
        move_particle_caches(args.game, args.cache_root)
        print('r16 disabled. Use the same launcher for r15 again.')
        return
    if not (args.game/'reach'/REPAIR).is_file():
        raise FileNotFoundError('Extract these tools beside your working ReachRBDoom3BFG.exe and apply r15 first.')
    settings = args.game/'reach-polish-inputs.json'
    previous = json.loads(settings.read_text()) if settings.is_file() else {}
    for key, title in [('donor', 'Choose your original reach-assets ZIP'),
                       ('effects', 'Choose your reach-effects ZIP'),
                       ('palette', 'Choose your collected reach-palette ZIP')]:
        value = getattr(args, key) or (Path(previous[key]) if key in previous and Path(previous[key]).exists() else None)
        setattr(args, key, value or choose(title))
    with ExitStack() as stack:
        build(unpack(args.donor, stack), unpack(args.effects, stack), args.palette,
              args.game, args.scale, args.lighting, args.cache_root)
    settings.write_text(json.dumps({k: str(getattr(args, k).resolve()) for k in ('donor', 'effects', 'palette')}, indent=2)+'\n')


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('Polish update failed: '+str(error), flush=True)
        raise SystemExit(1)
