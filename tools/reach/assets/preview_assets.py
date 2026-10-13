"""Software preview of converted MD5 geometry; does not launch either game."""
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from check_md5 import mesh, animation, skin


def render(output, clip, frame, width=640, height=360):
    output = Path(output); directory = output/'models/md5/weapons/reach_ar'
    names, parents, bind, surfaces = mesh(directory/'view.md5mesh')
    poses, _ = animation(directory/(clip+'.md5anim'), names, parents)
    vertices = skin(surfaces, poses[frame])
    mtr = (output/'materials/reach_ar.mtr').read_text()
    result = np.full((height, width, 3), [24, 29, 36], dtype=np.uint8)
    depth = np.full((height, width), np.inf)
    focal = width/(2*math.tan(math.radians(95)/2))
    light = np.array([-0.6, -0.2, 0.75]); light /= np.linalg.norm(light)
    for s, p in zip(surfaces, vertices):
        match = re.search(re.escape(s['material'])+r'\s*\{(.*?)(?:\n\})', mtr, re.S)
        tex = re.search(r'(?:diffusemap|\bmap)\s+([^\s]+)', match[1]) if match else None
        texture = np.array(Image.open(output/tex[1]).convert('RGBA')) if tex else np.full((1, 1, 4), [120, 140, 150, 255], dtype=np.uint8)
        additive = s['material'].split('/')[-1] in ('compass', 'display', 'item', 'ones', 'tens')
        pp = np.column_stack([width/2-p[:, 1]/np.maximum(p[:, 0], .01)*focal,
                              height/2-p[:, 2]/np.maximum(p[:, 0], .01)*focal])
        for tri in s['triangles']:
            source = p[tri]; z = source[:, 0]
            if (z < .1).any(): continue
            t = pp[tri]
            lo = np.maximum(np.floor(t.min(axis=0)).astype(int), [0, 0]); hi = np.minimum(np.ceil(t.max(axis=0)).astype(int), [width-1, height-1])
            if (hi < lo).any(): continue
            a, b, c = t
            denom = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denom) < 1e-8: continue
            x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
            w0 = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denom
            w1 = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denom
            weights = np.stack([w0, w1, 1-w0-w1], axis=-1)
            inverse = (weights/z).sum(axis=-1); zz = 1/np.maximum(inverse, 1e-10)
            d = depth[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            mask = (weights.min(axis=-1) >= -1e-6) & (zz < d)
            if not mask.any(): continue
            uv = np.einsum('...i,ij->...j', weights/z, s['uv'][tri])/inverse[..., None]
            # MD5 V addresses the top-origin image rows.
            tx = (uv[..., 0]*texture.shape[1]).astype(int) % texture.shape[1]
            ty = (uv[..., 1]*texture.shape[0]).astype(int) % texture.shape[0]
            rgba = texture[ty, tx]; alpha = rgba[..., 3].astype(float)/255
            n = np.cross(source[1]-source[0], source[2]-source[0]); n /= max(np.linalg.norm(n), 1e-9)
            shade = 1 if additive else .3+.7*abs(n @ light)
            color = rgba[..., :3].astype(float)*shade
            target = result[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            combined = np.clip(target.astype(float)+color*alpha[..., None], 0, 255) if additive else target*(1-alpha[..., None])+color*alpha[..., None]
            target[mask] = combined[mask].astype(np.uint8)
            d[mask & (alpha > .5)] = zz[mask & (alpha > .5)]
    image = Image.fromarray(result); draw = ImageDraw.Draw(image)
    draw.text((12, 12), f'{clip} / frame {frame}', fill=(230, 235, 240))
    return image


def contact_sheet(output):
    selections = [('idle', 0), ('fire_1_var1', 2), ('reload_empty', 22), ('melee_strike_1', 10), ('throw_grenade', 10), ('sprint_loop', 8)]
    sheet = Image.new('RGB', (1280, 1112), (12, 16, 22))
    ImageDraw.Draw(sheet).text((14, 12), 'Reach AR conversion - OFFLINE MESH PREVIEW - not captured in BFG', fill='white')
    for i, (clip, frame) in enumerate(selections):
        print('Preview:', clip, flush=True)
        sheet.paste(render(output, clip, frame), ((i % 2)*640, 32+(i//2)*360))
    path = Path(output)/'offline-preview.png'; sheet.save(path)
    return path


if __name__ == '__main__':
    import sys
    print(contact_sheet(sys.argv[1]))
