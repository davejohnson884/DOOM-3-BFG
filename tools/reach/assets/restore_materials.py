"""Restore working r15 surfaces while retaining the owner's accepted Steel paint.

Uses installed PK4s only. The TACPAD material and all four maps are copied
unchanged from r15. Only the two Steel armor diffuse maps come from r16 and
are returned to their original dimensions. No new material tuning is applied.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import uuid
import zipfile

from PIL import Image
from build_polish import (MATERIAL_FILE, PARTICLES, REPAIR, SURFACES, material_block,
                          move_particle_caches, PACK as POLISH_PACK)

PACK = 'zzzzzzzzzzzzz_reach_material_restore_r17.pk4'
PAINT = ('spartan_fp_armor', 'spartan_armor')
TACPAD = 'spartan_forearm_tricorder'
DIAGNOSTIC = 'reach_material_diagnostics.cfg'


def diffuse_path(text, name):
    body = material_block(text, 'reach/repair15/'+name)[0]
    match = re.search(r'\bdiffusemap\s+(textures/[^\s{}]+)', body)
    if not match: raise ValueError('Missing diffuse map for '+name)
    return match[1]


def find_polish(folder):
    current = folder/POLISH_PACK
    if current.is_file(): return current
    previous = sorted((p for p in folder.glob(POLISH_PACK+'.disabled-*') if p.is_file()),
                      key=lambda p: p.stat().st_mtime_ns, reverse=True)
    if previous: return previous[0]
    raise FileNotFoundError('The installed r16 PK4 is needed to retain your accepted Steel paint. Keep it in the reach folder, even if disabled.')


def diagnostic_cfg():
    lines = ['echo "Reach r17 material report: run while holding the Reach AR in a map"',
             'listImages namesort', 'conDump Reach-images-r17.log',
             'echo "Reach r17 active material definitions"',
             'r_skipBump', 'r_skipSpecular', 'r_skipDiffuse']
    lines += ['printMaterial reach/repair15/'+name for name in SURFACES]
    lines += ['conDump Reach-materials-r17.log']
    return ('\n'.join(lines)+'\n').encode()


def restore(game, cache_root=None):
    game = Path(game).resolve(); folder = game/'reach'
    original_path = folder/REPAIR; polish_path = find_polish(folder)
    if not original_path.is_file(): raise FileNotFoundError('Working r15 repair PK4 is missing: '+str(original_path))
    entries = {}; paint_report = {}; tacpad_hashes = {}
    with zipfile.ZipFile(original_path) as original, zipfile.ZipFile(polish_path) as polish:
        if original.testzip() or polish.testzip(): raise ValueError('An installed PK4 failed its CRC check')
        original_materials = original.read(MATERIAL_FILE).decode()
        polish_materials = polish.read(MATERIAL_FILE).decode()
        materials = original_materials
        for name in PAINT:
            old_path = diffuse_path(original_materials, name)
            current_path = diffuse_path(polish_materials, name)
            with Image.open(io.BytesIO(original.read(old_path))) as image:
                target_size = image.size
            with Image.open(io.BytesIO(polish.read(current_path))) as image:
                if image.size not in [target_size, tuple(v*2 for v in target_size)]:
                    raise ValueError('Unexpected installed armor texture dimensions: '+name)
                image = image.convert('RGBA')
                source_size = image.size
                if image.size != target_size:
                    image = image.resize(target_size, Image.Resampling.BOX)
                data = io.BytesIO(); image.save(data, format='TGA')
            path = 'textures/reach/restore17/'+name+'_diffuse.tga'
            entries[path] = data.getvalue()
            match = material_block(materials, 'reach/repair15/'+name)
            body = match[0].replace(old_path, path)
            materials = materials[:match.start()]+body+materials[match.end():]
            paint_report[name] = {'inputSize': source_size, 'outputSize': target_size,
                                  'acceptedPaintSource': current_path,
                                  'sourceSha256': hashlib.sha256(polish.read(current_path)).hexdigest()}
        # The original TACPAD declaration and pixels are the rollback contract.
        # Keep its complete diffuse, normal, specular and self-illumination maps.
        for role in ('diffuse', 'normal', 'specular', 'illum'):
            path = 'textures/reach/repair15/'+TACPAD+'_'+role+'.tga'
            entries[path] = original.read(path)
            tacpad_hashes[role] = hashlib.sha256(entries[path]).hexdigest()
        if material_block(materials, 'reach/repair15/'+TACPAD)[0] != material_block(original_materials, 'reach/repair15/'+TACPAD)[0]:
            raise ValueError('TACPAD material changed during restoration')
        # This is a material rollback: retain the currently installed r16 FX.
        # Copy them into this pack so disabling r16 does not remove the effects.
        for name in ('ar_round', 'ar_long', 'frag_fireball', 'smoke', 'blast'):
            shader = 'reach/effects15/'+name
            old = material_block(materials, shader)
            materials = materials[:old.start()]+material_block(polish_materials, shader)[0]+materials[old.end():]
        for item in polish.infolist():
            if item.filename.startswith('textures/reach/effects16/'):
                entries[item.filename] = polish.read(item)
        for name in PARTICLES:
            path = 'particles/'+name+'.prt'; entries[path] = polish.read(path)
        entries[MATERIAL_FILE] = materials.encode()
        entries[DIAGNOSTIC] = diagnostic_cfg()
        for name in SURFACES:
            body = material_block(materials, 'reach/repair15/'+name)[0]
            if 'rmaomap' in body: raise ValueError('Experimental PBR material remains: '+name)
            if name not in PAINT:
                if body != material_block(original_materials, 'reach/repair15/'+name)[0]:
                    raise ValueError('Working material was changed: '+name)
        for path in re.findall(r'\b(?:map|bumpmap|diffusemap|specularmap)\s+(textures/[^\s{}]+)', materials):
            if path not in entries and path not in original.namelist():
                raise ValueError('Restored texture reference does not resolve: '+path)
    report = {'revision': 'r17', 'purpose': 'Restore original-resolution working materials; keep accepted armor paint',
              'sourceR15Sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
              'sourceR16Sha256': hashlib.sha256(polish_path.read_bytes()).hexdigest(),
              'tacpad': {'materialByteIdenticalToR15': True, 'originalTextureSha256': tacpad_hashes},
              'paint': paint_report, 'surfaceLighting': 'Original r15 bump/specular materials, without r16 PBR rewrite',
              'effects': 'Copied unchanged from the installed r16 pack',
              'modelChanged': False, 'poseChanged': False, 'animationChanged': False, 'gameplayChanged': False,
              'upscaleRemoved': True, 'runtimeTest': 'Owner verification required; root cause of flat in-game response remains unproven',
              'files': {n: hashlib.sha256(b).hexdigest() for n, b in entries.items()}}
    entries['reach-material-restore17-report.json'] = json.dumps(report, indent=2).encode()
    destination = folder/PACK
    with tempfile.NamedTemporaryFile(dir=folder, prefix='reach-restore-', suffix='.tmp', delete=False) as handle:
        staged = Path(handle.name)
    try:
        with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()): archive.writestr(name, data)
        with zipfile.ZipFile(staged) as archive:
            if archive.testzip(): raise ValueError('Material restore PK4 failed CRC validation')
        report['particleCacheBackups'] = move_particle_caches(game, cache_root)
        if destination.exists():
            destination.rename(destination.with_name(destination.name+'.backup-'+uuid.uuid4().hex[:12]))
        staged.replace(destination)
        current = folder/POLISH_PACK
        if current.is_file():
            backup = current.with_name(current.name+'.disabled-r17-'+uuid.uuid4().hex[:12])
            current.rename(backup); report['disabledR16Pack'] = str(backup)
    finally: staged.unlink(missing_ok=True)
    (game/'reach-material-restore17-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Restored the r15 TACPAD and original-resolution bump/specular materials.')
    print('Accepted Steel armor paint retained. r16 effects retained without changes.')
    print('Use your usual Play-Reach-projection.cmd.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--cache-root', type=Path, help='Optional custom fs_savepath')
    args = parser.parse_args(); restore(args.game, args.cache_root)


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('Material restore failed: '+str(error), flush=True)
        raise SystemExit(1)
