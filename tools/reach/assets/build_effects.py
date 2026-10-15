"""Convert a private focused Reach export to a drop-in flash/frag PK4.

Donor artwork stays on the owner's PC. Blam particle palettes and sprite UV
rectangles are baked to standard BFG materials; unsupported function curves
are approximated explicitly, never described as a shader-identical port.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import zipfile

import numpy as np
from PIL import Image
from build_appearance import extract, material, normalize, rgba_tga
from convert_reach import read_dds, slug
from rmf_reader.SceneReader import SceneReader

PACK = 'zzzzzzzzzz_reach_effects.pk4'
FRAG_TAG = 'objects\\weapons\\grenade\\frag_grenade\\frag_grenade'


def record(bundle, tag, kind):
    file = Path(bundle)/'effect-metadata'/(slug(tag)+'.'+kind+'.json')
    return json.loads(file.read_text())


def sample_wrap(pixels, u, v):
    """Bilinear repeat sampling of source UV rectangles, including tiled UVs."""
    h,w = pixels.shape[:2]
    x,y = u*w-.5,v*h-.5
    ix,iy = np.floor(x).astype(int),np.floor(y).astype(int)
    fx,fy = (x-ix)[...,None],(y-iy)[...,None]
    a = pixels[iy%h,ix%w]*(1-fx)+pixels[iy%h,(ix+1)%w]*fx
    b = pixels[(iy+1)%h,ix%w]*(1-fx)+pixels[(iy+1)%h,(ix+1)%w]*fx
    return a*(1-fy)+b*fy


def sprite_rectangles(particle):
    # Assembly's two runtime arrays share the name Unknown; the collector
    # retains the latter (RuntimeMFrames), whose first record holds the count.
    rows = [struct.unpack('<4f',base64.b64decode(x['raw'])) for x in particle['children']['Unknown']['elements']]
    count = round(rows[0][0])
    if count<1 or count>64 or count!=len(rows)-1: raise ValueError('Unsupported particle sprite frame table')
    if not np.isfinite(rows).all(): raise ValueError('Nonfinite sprite rectangle')
    return rows[1:]


def bitmap(bundle, tag):
    path = Path(bundle)/'effect-bitmaps'/(slug(tag)+'_000.dds')
    return np.asarray(read_dds(path),dtype=float)/255


def bake_palette(bundle, particle_tag, bitmap_tag, palette_tag, size, palette_ages=(0.,)):
    rects = sprite_rectangles(record(bundle,particle_tag,'prt3'))
    source,palette = bitmap(bundle,bitmap_tag),bitmap(bundle,palette_tag)
    width,height = size
    uu,vv = np.meshgrid((np.arange(width)+.5)/width,(np.arange(height)+.5)/height)
    tiles = []
    for age in palette_ages:
        for u,v,su,sv in rects:
            noise = sample_wrap(source,u+uu*su,v+vv*sv)
            intensity = np.clip(noise[...,0],0,1)
            row = min(palette.shape[0]-1,round(age*(palette.shape[0]-1)))
            ramp = palette[row]
            x = intensity*(len(ramp)-1);lo = np.floor(x).astype(int);hi = np.minimum(lo+1,len(ramp)-1)
            color = ramp[lo]*(1-(x-lo)[...,None])+ramp[hi]*(x-lo)[...,None]
            # Additive RGB must be black outside the source sprite. Retain
            # source alpha as coverage; do not invent a star-shaped flash.
            color[...,:3] *= noise[...,3,None]
            color[...,3] = noise[...,3]
            tiles.append(color)
    return np.concatenate(tiles,axis=1),len(tiles)


def sprite_material(name,path,blend='add'):
    return f'''{name}
{{
    twoSided
    noShadows
    translucent
    {{
        blend {blend}
        map {path}
        vertexColor
    }}
}}
'''


def stage(material,life,size,aspect=1,orientation='view',offset='0 0 0',angle=0,frames=0,count=1,speed='0',fade=.85,color='1 1 1 1',delay=0):
    return f'''    {{
        count {count}
        material {material}
        time {life:.6g}
        cycles 1
        timeOffset {delay:.6g}
        bunching 1
        distribution rect 0 0 0
        direction cone 30
        orientation {orientation}
        offset {offset}
        speed {speed}
        size {size}
        aspect {aspect}
        initialAngle {angle}
        rotation 0
        randomDistribution 0
        gravity 0
        animationFrames {frames}
        fadeIn 0
        fadeOut {fade}
        color {color}
    }}
'''


def frag_obj(scene):
    model = scene.model_pool[0]
    if len(model.bones)!=1 or model.bones[0].parent_index!=-1: raise ValueError('Expected rigid frag model')
    permutation = next(p for r in model.regions if r.name=='default' for p in r.permutations if p.name=='default')
    if permutation.mesh_count!=1: raise ValueError('Unexpected frag mesh count')
    mesh = model.meshes[permutation.mesh_index]
    vb = scene.vertex_buffer_pool[mesh.vertex_buffer_index]
    ib = scene.index_buffer_pool[mesh.index_buffer_index]
    positions = np.array([list(v)[:3]+[1] for v in vb.position_channels[0]])@np.array(mesh.vertex_transform)
    positions = positions@np.array(model.bones[0].transform)
    positions = positions[:,:3]*120
    center = (positions.min(axis=0)+positions.max(axis=0))*.5
    positions -= center
    uv = np.array([list(v)[:2]+[0,1] for v in vb.texcoord_channels[0]])@np.array(mesh.texture_transform)
    normals = normalize(np.array([list(v)[:3] for v in vb.normal_channels[0]])@np.array(model.bones[0].transform)[:3,:3])
    lines = ['# Reach rigid frag, source units converted to BFG inches; centered for spin']
    lines += ['v '+' '.join(f'{x:.9g}' for x in p) for p in positions]
    # This host's OBJ parser flips V; source RMF/MD5 data uses top-origin V.
    lines += [f'vt {p[0]:.9g} {1-p[1]:.9g}' for p in uv]
    lines += ['vn '+' '.join(f'{x:.9g}' for x in n) for n in normals]
    triangles = 0
    for i,segment in enumerate(mesh.segments):
        shader = scene.material_pool[segment.material_index].name
        lines += [f'g frag_{i}','usemtl reach/'+slug(shader)]
        for a,b,c in ib.get_triangles(segment):
            lines.append('f '+' '.join(f'{v+1}/{v+1}/{v+1}' for v in [a,c,b]))
            triangles += 1
    return ('\n'.join(lines)+'\n').encode(),{'vertices':len(positions),'triangles':triangles,'centerShift':center.tolist(),
                                              'bounds':[positions.min(axis=0).tolist(),positions.max(axis=0).tolist()]}


def source_tuning(bundle):
    data = base64.b64decode(record(bundle,FRAG_TAG,'proj')['raw'])
    damage_tag = FRAG_TAG.rsplit('\\',1)[0]+'\\damage_effects\\frag_grenade_explosion'
    dmg = base64.b64decode(record(bundle,damage_tag,'jpt!')['raw'])
    timer_mode = struct.unpack_from('<h',data,0x16C)[0]
    arming = struct.unpack_from('<f',data,0x174)[0]
    timer = struct.unpack_from('<2f',data,0x184)
    gravity_scale = struct.unpack_from('<f',data,0x2B8)[0]
    radius = struct.unpack_from('<2f',dmg,0)
    damage = struct.unpack_from('<2f',dmg,0x24)
    if timer_mode!=1 or not 0<timer[0]<=timer[1]<5 or not 0<arming<5: raise ValueError('Unsupported frag timer data')
    return {'timerStarts':'first floor bounce','armingTime':arming,'timerRange':timer,
            'airGravityScale':gravity_scale,'damage':sum(damage)/2,'radiusBfg':radius[1]*120,
            'coreRadiusBfg':radius[0]*120,'throwVelocityBfg':720,
            'limitations':['Throw speed is retained from r13: player throw globals were not exported.',
                           'Gravity scale applies to BFG gravity; Halo global gravity is not known.',
                           'BFG radius damage retains its own falloff/obstruction rules.']}


def frag_definition(tuning):
    return f'''// Reach model, source floor-bounce timer/arming delay and splash magnitude.
entityDef projectile_reach_frag {{
    "inherit" "projectile_grenade"
    "model" "models/reach/frag_grenade.obj"
    "offsetModel" "0 0 0"
    "mins" "-3 -3 -3"
    "maxs" "3 3 3"
    "cylinder" "8"
    "def_damage" "damage_reach_frag_contact"
    "def_splash_damage" "damage_reach_frag_splash"
    "velocity" "720 0 0"
    "mass" "0.4"
    "gravity" "{1066*tuning['airGravityScale']:.7g}"
    "linear_friction" "0.05"
    "angular_friction" "0.4"
    "contact_friction" "0.42"
    "bounce" "0.3"
    "fuse" "45"
    "detonate_on_fuse" "0"
    "reach_floor_fuse" "1"
    "reach_arming_time" "{tuning['armingTime']:.7g}"
    "reach_bounce_timer_min" "{tuning['timerRange'][0]:.7g}"
    "reach_bounce_timer_max" "{tuning['timerRange'][1]:.7g}"
    "detonate_on_world" "0"
    "detonate_on_actor" "0"
    "detonate_on_trigger" "0"
    "smoke_fly" ""
    "smoke_bounce" ""
    "debris_count" "0"
    "impact_damage_effect" "0"
    "model_detonate" "reach_frag_explosion.prt"
    "remove_time" "3500"
    "snd_bounce" "reach_frag_bounce14"
    "snd_explode" "reach_frag_explode14"
}}
entityDef damage_reach_frag_contact {{
    "damage" "0"
    "push" "0"
}}
entityDef damage_reach_frag_splash {{
    "inherit" "damage_grenadeSplash"
    "damage" "{round(tuning['damage'])}"
    "radius" "{tuning['radiusBfg']:.7g}"
    "push" "3000"
    "knockback" "30"
    "attackerDamageScale" "1"
}}
'''


def build(bundle,original,output):
    bundle,output = Path(bundle),Path(output)
    manifest = json.loads((bundle/'manifest.json').read_text())
    if manifest.get('schemaVersion')!=2: raise ValueError('Choose the focused reach-effects ZIP, not the earlier arms export')
    entries = {}; material_text = ''
    base = 'objects\\weapons\\rifle\\assault_rifle\\fx\\particles\\'
    fire = 'fx\\bitmaps\\weapon_fire\\'
    specs = [('ar_round',base+'muzzle_flash_round',fire+'muzzle_flash_round_gaseous',fire+'gradients\\muzzle_flare_assault_rifle',(256,256),(0.,)),
             ('ar_long',base+'muzzle_flash_long',fire+'muzzle_flash_long_gaseous',fire+'gradients\\muzzle_flare_assault_rifle_long',(128,512),(0.,)),
             ('frag_fireball',FRAG_TAG.rsplit('\\',1)[0]+'\\fx\\particles\\fireball','fx\\bitmaps\\atmospheric_rolling\\fireball_plate','fx\\particles\\_gradients\\fireball_human',(128,128),(0.,.33,.66,1.))]
    frame_counts = {}
    for name,particle,texture,palette,size,ages in specs:
        print('Baking source sprite/palette:',name,flush=True)
        pixels,frames = bake_palette(bundle,particle,texture,palette,size,ages)
        path = 'textures/reach/effects14/'+name+'.tga';entries[path] = rgba_tga(pixels)
        material_text += sprite_material('reach/effects14/'+name,path)
        frame_counts[name] = frames
    for name,tag in [('smoke','fx\\bitmaps\\atmospheric\\soft_smoke_large'),('blast','fx\\bitmaps\\flash\\flash_soft')]:
        path = 'textures/reach/effects14/'+name+'.tga';entries[path] = rgba_tga(bitmap(bundle,tag))
        material_text += sprite_material('reach/effects14/'+name,path,'blend' if name=='smoke' else 'add')
    # Approximate the source's round + axial flash layers with stock BFG planes.
    flash = stage('reach/effects14/ar_round',.115,'3.5',offset='1.8 0 0',frames=frame_counts['ar_round'])
    flash += stage('reach/effects14/ar_long',.125,'1.8',4,'z',offset='7.2 0 0',angle=.001,frames=frame_counts['ar_long'])
    flash += stage('reach/effects14/ar_long',.125,'1.8',4,'y',offset='7.2 0 0',angle=270,frames=frame_counts['ar_long'])
    entries['particles/reach_ar_flash.prt'] = ('particle reach_ar_flash.prt {\n'+flash+'}\n').encode()
    explosion = stage('reach/effects14/blast',.12,'25 to 55',fade=1)
    explosion += stage('reach/effects14/frag_fireball',.65,'22 to 60',frames=frame_counts['frag_fireball'],count=3,speed='0 to 30',fade=.8)
    explosion += stage('reach/effects14/smoke',2.3,'25 to 85',count=5,speed='15 to 40',fade=.8,color='.18 .17 .15 .5',delay=.06)
    entries['particles/reach_frag_explosion.prt'] = ('particle reach_frag_explosion.prt {\n'+explosion+'}\n').encode()
    rmf = next(bundle.rglob('*.rmf')); scene = SceneReader.open_scene(str(rmf))
    obj,geometry = frag_obj(scene);entries['models/reach/frag_grenade.obj'] = obj
    for mat in scene.material_pool:
        material_text += material(scene,mat,bundle,entries)
    entries['materials/reach_effects14.mtr'] = material_text.encode()
    tuning = source_tuning(bundle)
    entries['def/reach_frag.def'] = frag_definition(tuning).encode()
    with zipfile.ZipFile(original) as archive:
        sound_text = ''
        for name,token in [('bounce','_frag_bnc_metal_'),('explode','_frag_expl_reach_')]:
            files = sorted(n for n in archive.namelist() if n.startswith('sound/reach/') and token in n and n.endswith('.wav'))
            if not files: raise ValueError('Missing existing Reach frag sound group: '+name)
            sound_text += 'reach_frag_'+name+'14\n{\n    minDistance 5\n    maxDistance '+('25' if name=='bounce' else '100')+'\n'+'\n'.join('    '+n for n in files)+'\n}\n'
        entries['sound/reach_frag14.sndshd'] = sound_text.encode()
    report = {'revision':'effects-r14','sourceBuild':manifest['BuildString'],'geometry':geometry,
              'spriteFrames':frame_counts,'frag':tuning,'poseChanged':False,'scriptsChanged':False,
              'requires':'r14 Reach executable for first-floor frag fuse; keep r13/private/TACPAD packs installed',
              'sourceIssues':manifest.get('errors',[]),'runtimePlaytest':'not run in cloud',
              'limitations':['Particle timing, scale and palettes are adapted to BFG stages; source function curves were not exported.',
                             'No Blam shader bytecode or lighting LUTs are used.'],
              'files':{p:hashlib.sha256(b).hexdigest() for p,b in entries.items()}}
    entries['reach-effects14-build.json'] = json.dumps(report,indent=2).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError('Keep your previous pack or choose a new output filename: '+str(output))
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(entries.items()):archive.writestr(name,data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None: raise ValueError('PK4 CRC check failed')
    print('Created '+str(output)+'. Copy the generated reach folder into your Doom game folder.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor',type=Path)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=Path.cwd()/'reach'/PACK)
    args = parser.parse_args()
    original = args.game/'reach/zzz_reach_ar.pk4'
    if not original.is_file(): raise FileNotFoundError('Installed Reach AR PK4 not found: '+str(original))
    if not (args.game/'reach/zzzzzzzzz_reach_input.pk4').is_file(): raise FileNotFoundError('Install the complete r14 combat update first.')
    if args.donor is None:
        import tkinter as tk
        from tkinter.filedialog import askopenfilename
        root=tk.Tk();root.withdraw()
        selected=askopenfilename(title='Select the new reach-effects ZIP',filetypes=[('Reach effects ZIP','*.zip')]);root.destroy()
        if not selected:raise ValueError('No source selected; no game files changed')
        args.donor=Path(selected)
    if args.donor.is_dir():build(args.donor,original,args.out)
    else:
        with tempfile.TemporaryDirectory(prefix='reach-effects-') as temp:
            with zipfile.ZipFile(args.donor) as archive:extract(archive,Path(temp))
            build(Path(temp),original,args.out)


if __name__=='__main__':main()
