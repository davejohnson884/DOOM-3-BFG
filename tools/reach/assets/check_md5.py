"""Independent MD5 reader using BFG's positive-W quaternion convention.

Used to validate text outputs and render an offline conversion preview.
This is a format/skinning check, not evidence of an in-game playtest.
"""
import json
import math
import re
from pathlib import Path

import numpy as np


def engine_matrix(xyz, translation):
    x, y, z = xyz
    # neo/idlib/math/Quat.h: idQuat::CalcW and idCQuat::ToQuat.
    w = math.sqrt(abs(1-x*x-y*y-z*z))
    # ToMat3's three vectors are axes/columns (Matrix.h operator*).
    m = np.array([[1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w), translation[0]],
                  [2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w), translation[1]],
                  [2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y), translation[2]],
                  [0, 0, 0, 1]])
    return m


def mesh(path):
    text = Path(path).read_text()
    count = int(re.search(r'numJoints\s+(\d+)', text)[1])
    joint_text = re.search(r'joints\s*\{(.*?)\}', text, re.S)[1]
    names = []; parents = []; matrices = []
    for n, parent, translation, xyz in re.findall(r'"([^"\n]+)"\s+(-?\d+)\s*\(([^)]+)\)\s*\(([^)]+)\)', joint_text):
        names.append(n); parents.append(int(parent))
        matrices.append(engine_matrix(list(map(float, xyz.split())), list(map(float, translation.split()))))
    if len(names) != count or len(set(names)) != count or parents[0] != -1:
        raise ValueError('Invalid MD5 joints')
    surfaces = []
    for block in re.findall(r'\bmesh\s*\{(.*?)\}', text, re.S):
        vertices = [(int(i), list(map(float, uv.split())), int(first), int(amount)) for i, uv, first, amount in
                    re.findall(r'\bvert\s+(\d+)\s*\(([^)]+)\)\s+(\d+)\s+(\d+)', block)]
        weights = [(int(i), int(j), float(b), list(map(float, p.split()))) for i, j, b, p in
                   re.findall(r'\bweight\s+(\d+)\s+(\d+)\s+([^\s]+)\s*\(([^)]+)\)', block)]
        tris = [tuple(map(int, t)) for t in re.findall(r'\btri\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', block)]
        nv = int(re.search(r'numverts\s+(\d+)', block)[1]); nw = int(re.search(r'numweights\s+(\d+)', block)[1]); nt = int(re.search(r'numtris\s+(\d+)', block)[1])
        if (len(vertices), len(weights), len(tris)) != (nv, nw, nt): raise ValueError('MD5 surface count mismatch')
        if [v[0] for v in vertices] != list(range(nv)) or [w[0] for w in weights] != list(range(nw)):
            raise ValueError('Nonsequential vertex/weight indices')
        for _, uv, first, amount in vertices:
            if amount < 1 or amount > 4 or first+amount > nw or not np.isclose(sum(w[2] for w in weights[first:first+amount]), 1, atol=0.00001):
                raise ValueError('Invalid vertex skin weights')
        if any(j < 0 or j >= count for _, j, _, _ in weights): raise ValueError('Bad skin joint')
        if any(any(v < 0 or v >= nv for v in t[1:]) for t in tris): raise ValueError('Bad triangle index')
        surfaces.append({'material': re.search(r'shader\s+"([^"\n]+)"', block)[1], 'uv': np.array([v[1] for v in vertices]),
                         'starts': np.array([v[2] for v in vertices]), 'joints': np.array([w[1] for w in weights]),
                         'bias': np.array([w[2] for w in weights]), 'offsets': np.array([w[3] for w in weights]),
                         'triangles': np.array([t[1:] for t in tris])})
    if len(surfaces) != int(re.search(r'numMeshes\s+(\d+)', text)[1]): raise ValueError('Bad mesh count')
    return names, parents, np.array(matrices), surfaces


def animation(path, names, parents):
    text = Path(path).read_text()
    count = int(re.search(r'numFrames\s+(\d+)', text)[1]); nj = int(re.search(r'numJoints\s+(\d+)', text)[1])
    if nj != len(names) or int(re.search(r'frameRate\s+(\d+)', text)[1]) != 30: raise ValueError('Incompatible clip')
    rows = re.findall(r'"([^"\n]+)"\s+(-?\d+)\s+(\d+)\s+(\d+)', re.search(r'hierarchy\s*\{(.*?)\}', text, re.S)[1])
    if [(n, int(p)) for n, p, _, _ in rows] != list(zip(names, parents)): raise ValueError('Clip/mesh skeleton mismatch')
    if any(int(flags) != 63 or int(start) != i*6 for i, (_, _, flags, start) in enumerate(rows)): raise ValueError('Unsupported compressed MD5 channels')
    blocks = re.findall(r'\bframe\s+(\d+)\s*\{(.*?)\}', text, re.S)
    if len(blocks) != count: raise ValueError('Missing frame data')
    frames = []
    for index, block in blocks:
        values = np.array(list(map(float, block.split())))
        if int(index) != len(frames) or len(values) != nj*6 or not np.isfinite(values).all(): raise ValueError('Bad animation components')
        values = values.reshape(nj, 6)
        matrices = np.array([engine_matrix(v[3:], v[:3]) for v in values])
        for i, parent in enumerate(parents):
            if parent >= i or parent < -1: raise ValueError('Invalid animation parent')
            if parent >= 0: matrices[i] = matrices[parent] @ matrices[i]
        frames.append(matrices)
    bounds = re.findall(r'\(([^)]+)\)\s*\(([^)]+)\)', re.search(r'bounds\s*\{(.*?)\}', text, re.S)[1])
    if len(bounds) != count: raise ValueError('Missing bounds')
    return np.array(frames), np.array([[list(map(float, a.split())), list(map(float, b.split()))] for a, b in bounds])


def skin(surfaces, matrices):
    positions = []
    for s in surfaces:
        weights = np.einsum('wij,wj->wi', matrices[s['joints'], :3, :3], s['offsets'])+matrices[s['joints'], :3, 3]
        positions.append(np.add.reduceat(weights*s['bias'][:, None], s['starts']))
    return positions


def check(output, original_world=None):
    output = Path(output); directory = output/'models/md5/weapons/reach_ar'
    names, parents, bind, surfaces = mesh(directory/'view.md5mesh')
    maximum_error = 0.; clips = {}; frames_checked = 0
    for path in sorted(directory.glob('*.md5anim')):
        frames, bounds = animation(path, names, parents)
        if original_world is not None:
            expected = original_world[path.stem].copy(); expected[..., :3, 3] *= 120
            maximum_error = max(maximum_error, float(np.abs(frames-expected).max()))
            if not np.allclose(frames, expected, atol=0.005): raise ValueError('BFG transform convention differs from source: '+path.stem)
        for frame, box in zip(frames, bounds):
            points = np.concatenate(skin(surfaces, frame))
            if not np.isfinite(points).all() or (points < box[0]-0.005).any() or (points > box[1]+0.005).any():
                raise ValueError('Bounds fail to contain skinned geometry: '+path.stem)
            frames_checked += 1
        clips[path.stem] = len(frames)
    report = {'joints': len(names), 'surfaces': len(surfaces), 'clips': len(clips), 'framesChecked': frames_checked,
              'maximumSerializedTransformError': maximum_error, 'checks': ['skeleton/indices', 'normalized skin weights', 'BFG positive-W transforms', 'all-frame skin bounds'],
              'inGameTest': 'not run'}
    (output/'validation-report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
