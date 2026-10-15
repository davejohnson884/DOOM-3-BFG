"""Build private TACPAD/Noble Six material overrides from an existing donor ZIP.

Only model/material/texture files and animation bounds are written. Source
animations, the accepted pose, the counter skin and gameplay remain untouched.
"""
import argparse
import io
import json
from pathlib import Path
import re
import tempfile
import time
import zipfile

import numpy as np
from PIL import Image
from convert_reach import convert_meshes, read_dds, slug, write_mesh
from rmf_reader.SceneReader import SceneReader
from check_md5 import mesh, animation, skin

MODEL = 'models/md5/weapons/reach_ar/'
PALETTE_LINEAR = np.array([.28, .30, .32])  # art-match starting point, not recovered retail RGB
TARGET = 'zzzzzzzz_reach_appearance.pk4'


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def tiled(image, size, tiling):
    """Periodic bilinear sampling, prefiltered for the bake's texel footprint."""
    width, height = size
    tx, ty = tiling
    if tx <= 0 or ty <= 0 or tx > 256 or ty > 256: raise ValueError('Invalid donor texture tiling')
    image = image.resize((min(image.width, max(1, round(width/tx))),
                          min(image.height, max(1, round(height/ty)))), Image.Resampling.BOX)
    pixels = np.asarray(image, dtype=np.float32)/255
    x = (np.arange(width, dtype=np.float32)+.5)*tx*image.width/width-.5
    y = (np.arange(height, dtype=np.float32)+.5)*ty*image.height/height-.5
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x-ix)[None,:,None], (y-iy)[:,None,None]
    top = pixels[iy[:,None]%image.height, ix[None,:]%image.width]*(1-fx) + pixels[iy[:,None]%image.height, (ix[None,:]+1)%image.width]*fx
    bottom = pixels[(iy[:,None]+1)%image.height, ix[None,:]%image.width]*(1-fx) + pixels[(iy[:,None]+1)%image.height, (ix[None,:]+1)%image.width]*fx
    return top*(1-fy)+bottom*fy


def normal(pixels):
    xy = pixels[..., :2]*2-1
    return normalize(np.dstack([xy, np.sqrt(np.maximum(0,1-(xy*xy).sum(axis=-1)))]))


def combine_normals(base, detail):
    # Reoriented normal mapping; a neutral detail map leaves the base unchanged.
    a = base.copy(); a[...,2] += 1
    b = detail*np.array([-1,-1,1])
    return normalize(a*(a*b).sum(axis=-1,keepdims=True)/np.maximum(a[...,2,None],1e-5)-b)


def rgba_tga(pixels):
    pixels = np.clip(np.rint(pixels*255),0,255).astype(np.uint8)
    if pixels.shape[-1] == 3:
        pixels = np.dstack([pixels,np.full(pixels.shape[:2],255,dtype=np.uint8)])
    result = io.BytesIO(); Image.fromarray(pixels).save(result,format='TGA'); return result.getvalue()


def material(scene, mat, bundle, entries):
    maps = {m.texture_usage:m for m in mat.texture_mappings}
    def sample(usage,size=None):
        mapping = maps[usage]
        source_name = scene.texture_pool[mapping.texture_index].name
        source = next(bundle.rglob(slug(source_name)+'.dds'),None)
        if source is None: raise ValueError('Missing donor texture: '+source_name)
        image = read_dds(source)
        return tiled(image,size or image.size,mapping.tiling)
    # Use the original albedo resolution, with a hard limit for user-supplied data.
    mapping = maps['diffuse']; source_name = scene.texture_pool[mapping.texture_index].name
    image = read_dds(next(bundle.rglob(slug(source_name)+'.dds')))
    if max(image.size)>4096: raise ValueError('Texture exceeds conversion limit')
    size = image.size
    diffuse = sample('diffuse',size)[...,:3]
    if 'color_change' in maps:
        # Both armor color channels use steel. Combining RGB masks avoids
        # assigning an unverified primary/secondary channel order.
        mask = np.clip(sample('color_change',size)[...,:3].sum(axis=-1,keepdims=True),0,1)
        linear = np.where(diffuse<=.04045,diffuse/12.92,((diffuse+.055)/1.055)**2.4)
        linear *= (1-mask)+mask*PALETTE_LINEAR
        diffuse = np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
    if 'diffuse_detail' in maps:
        # A conservative neutral-detail approximation, not Blam's BRDF.
        diffuse *= .65+.35*sample('diffuse_detail',size)[...,:3]*2
    tints = {t.tint_usage:np.array(t.tint_color[:3])/255 for t in mat.tints}
    diffuse *= tints.get('albedo',1)
    normals = normal(sample('normal',size))
    if 'normal_detail' in maps:
        normals = combine_normals(normals,normal(sample('normal_detail',size)))
    spec = sample('specular',size)
    if int(maps['specular'].channel_mask)==8: spec = np.repeat(spec[...,3,None],3,axis=-1)
    else: spec = spec[...,:3]
    spec *= tints.get('specular',1)
    name = slug(mat.name); prefix = 'textures/reach/appearance/'+name
    for usage,pixels in [('diffuse',diffuse),('normal',normals*.5+.5),('specular',spec)]:
        entries[prefix+'_'+usage+'.tga'] = rgba_tga(pixels)
    text = f'reach/{name}\n{{\n    bumpmap {prefix}_normal.tga\n    diffusemap {prefix}_diffuse.tga\n    specularmap {prefix}_specular.tga\n'
    if 'self_illum' in maps:
        entries[prefix+'_illum.tga'] = rgba_tga(sample('self_illum',size)[...,:3]*tints.get('self_illum',1))
        text += '    {\n        blend add\n        map '+prefix+'_illum.tga\n    }\n'
    return text+'}\n'


def extract(archive, root):
    if sum(i.file_size for i in archive.infolist())>1024**3: raise ValueError('ZIP exceeds extraction limit')
    for item in archive.infolist():
        path = Path(item.filename.replace('\\','/'))
        if path.is_absolute() or '..' in path.parts or ':' in item.filename: raise ValueError('Unsafe ZIP path')
    archive.extractall(root)


def build(bundle, original, output):
    bundle, original, output = Path(bundle), Path(original), Path(output)
    with tempfile.TemporaryDirectory(prefix='reach-appearance-') as directory, zipfile.ZipFile(original) as archive:
        temp = Path(directory)
        for item in archive.infolist():
            if item.filename.startswith(MODEL) and item.filename.endswith(('.md5mesh','.md5anim')):
                if item.file_size>8*1024*1024: raise ValueError('Model/animation exceeds limit')
                if '..' in Path(item.filename).parts: raise ValueError('Unsafe mod path')
                archive.extract(item,temp)
        text = archive.read(MODEL+'view.md5mesh').decode()
        names,parents,bind,surfaces = mesh(temp/MODEL/'view.md5mesh')
        if len(names)!=56 or names[0]!='origin': raise ValueError('Expected the existing 56-joint Reach AR conversion')
        rmf = next((p for p in bundle.rglob('*.rmf') if 'spartans_fp_fp' in p.name),None)
        if rmf is None: raise ValueError('Choose the original reach-assets ZIP containing the full Spartan FP arm model')
        scene = SceneReader.open_scene(str(rmf)); arms = scene.model_pool[0]
        permutation = next(p for r in arms.regions if r.name=='flair_forearm' for p in r.permutations if p.name=='carter')
        source_names = names.copy(); source_names[0] = 'pedestal'
        addon = convert_meshes(scene,arms,range(permutation.mesh_index,permutation.mesh_index+permutation.mesh_count),source_names)
        if {s['material'] for s in addon}!={'spartan_forearm_tricorder'}: raise ValueError('TACPAD permutation changed')
        q = np.tile([0.,0.,0.,1.],(len(names),1)); t = np.zeros((len(names),3))
        write_mesh(temp/'addon.md5mesh',names,[-1]*len(names),q,t,addon)
        blocks = re.findall(r'\bmesh\s*\{.*?\}',(temp/'addon.md5mesh').read_text(),re.S)
        text = re.sub(r'numMeshes\s+\d+','numMeshes '+str(len(surfaces)+len(blocks)),text,count=1)
        text += '\n'+'\n'.join(blocks)+'\n'
        (temp/MODEL/'view.md5mesh').write_text(text)
        nn,pp,bb,full = mesh(temp/MODEL/'view.md5mesh')
        assert nn==names and pp==parents and np.array_equal(bb,bind)
        entries = {MODEL+'view.md5mesh':text.encode()}
        frames_checked = 0
        for file in sorted((temp/MODEL).glob('*.md5anim')):
            frames,bounds = animation(file,names,parents)
            rows = []
            for frame,box in zip(frames,bounds):
                points = np.concatenate(skin(full,frame))
                lo = np.minimum(box[0],points.min(axis=0)-.1); hi = np.maximum(box[1],points.max(axis=0)+.1)
                rows.append('    ( '+' '.join(f'{v:.9g}' for v in lo)+' ) ( '+' '.join(f'{v:.9g}' for v in hi)+' )')
                frames_checked += 1
            original_text = file.read_text()
            changed = re.sub(r'\bbounds\s*\{.*?\}',lambda _: 'bounds {\n'+'\n'.join(rows)+'\n}',original_text,count=1,flags=re.S)
            assert re.sub(r'\bbounds\s*\{.*?\}','',changed,flags=re.S)==re.sub(r'\bbounds\s*\{.*?\}','',original_text,flags=re.S)
            entries[MODEL+file.name] = changed.encode()
        if frames_checked!=844: raise ValueError('Expected 25 original clips / 844 frames')
        mtr = archive.read('materials/reach_ar.mtr').decode()
        used = {s['material'].removeprefix('reach/') for s in full}
        for file in bundle.rglob('*.rmf'):
            source = SceneReader.open_scene(str(file))
            for mat in source.material_pool:
                if mat.name not in used or mat.alpha_mode!='opaque': continue
                if not (mat.name.startswith('spartan_') or mat.name.startswith('assault_rifle_')): continue
                print('Converting detail/color/specular:',mat.name,flush=True)
                body = material(source,mat,bundle,entries)
                pattern = r'reach/'+re.escape(slug(mat.name))+r'\s*\{(?:[^{}]|\{[^{}]*\})*\}'
                if re.search(pattern,mtr): mtr = re.sub(pattern,lambda _: body,mtr,count=1)
                elif mat.name=='spartan_forearm_tricorder': mtr += '\n'+body
                else: raise ValueError('Expected original material: '+mat.name)
        entries['materials/reach_ar.mtr'] = mtr.encode()
        report = {'variant':'default Spartan arms + carter/TACPAD forearm',
                  'palette':'Steel on both armor channels, approximate linear tint',
                  'paletteLinearRGB':PALETTE_LINEAR.tolist(), 'clips':25, 'framesChecked':frames_checked,
                  'motionChanged':False,'poseChanged':False,'runtimeTest':'Owner playtest required',
                  'limitations':['Detail maps baked at base-map resolution; BFG lighting differs from Blam.',
                                 'Palette is a visual starting point, not recovered retail player-color RGB.']}
        entries['reach-appearance-build.json'] = json.dumps(report,indent=2).encode()
        output.parent.mkdir(parents=True,exist_ok=True)
        # Preserve a previous appearance pack; never alter the donor/original mod.
        if output.exists(): output.rename(output.with_suffix('.pk4.backup-'+time.strftime('%Y%m%d-%H%M%S')))
        with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as result:
            for name,data in sorted(entries.items()): result.writestr(name,data)
        with zipfile.ZipFile(output) as result:
            if result.testzip() is not None: raise ValueError('Appearance PK4 CRC check failed')
        print('Created '+str(output)+'. Start the usual Play-Reach-projection.cmd. Remove this PK4 to undo.')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor',type=Path)
    parser.add_argument('--game',type=Path,required=True)
    args = parser.parse_args()
    original = args.game/'reach/zzz_reach_ar.pk4'
    if not original.is_file(): raise FileNotFoundError('Existing Reach AR pack not found: '+str(original))
    if args.donor is None:
        import tkinter as tk
        from tkinter.filedialog import askopenfilename
        window = tk.Tk(); window.withdraw()
        selected = askopenfilename(title='Select your original reach-assets ZIP',filetypes=[('Reach donor ZIP','*.zip')])
        window.destroy()
        if not selected: raise ValueError('No donor selected. No game files changed.')
        args.donor = Path(selected)
    output = args.game/'reach'/TARGET
    if args.donor.is_dir(): build(args.donor,original,output)
    else:
        with tempfile.TemporaryDirectory(prefix='reach-appearance-donor-') as directory:
            with zipfile.ZipFile(args.donor) as archive: extract(archive,Path(directory))
            build(Path(directory),original,output)


if __name__ == '__main__': main()
