"""Repackage existing private Reach conversions for released RBDoom3BFG."""
import argparse
import hashlib
import io
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

from build_weapon import replace_keys
from presentation import entries as presentation_entries

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
CATEGORIES = ('models', 'materials', 'textures', 'sound', 'def')


def tga(width, height, pixels):
    # Top-left-origin RGBA, uncompressed true color, stored BGRA.
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, width, height, 32, 0x28)
    return header + b''.join(bytes((b, g, r, a)) for r, g, b, a in pixels)


def digits():
    """Project-authored seven-segment glyphs; not missing donor digit images."""
    width, height = 640, 64
    pixels = [(0, 0, 0, 0)] * (width * height)
    segments = ((18, 7, 46, 12), (43, 11, 48, 31), (43, 33, 48, 53),
                (18, 52, 46, 57), (16, 33, 21, 53), (16, 11, 21, 31), (18, 29, 46, 34))
    patterns = ('abcdef', 'bc', 'abdeg', 'abcdg', 'bcfg', 'acdfg', 'acdefg', 'abc', 'abcdefg', 'abcdfg')
    for digit, pattern in enumerate(patterns):
        for letter in pattern:
            x0, y0, x1, y1 = segments[ord(letter)-ord('a')]
            for y in range(y0, y1):
                for x in range(x0, x1):
                    pixels[y*width+digit*64+x] = (50, 225, 255, 255)
    return tga(width, height, pixels)


def flash():
    pixels = []
    for y in range(64):
        for x in range(64):
            dx, dy = abs((x-31.5)/31.5), abs((y-31.5)/31.5)
            strength = max(0, 1-(dx*dx+dy*dy)**.5)**2
            ray = max(0, 1-min(dx, dy)*14) * max(0, 1-max(dx, dy))**2
            value = min(1, strength+ray*.7)
            pixels.append((round(255*value), round(205*value), round(90*value), 255))
    return tga(64, 64, pixels)


def effect_material():
    return '''reach/ar_flash
{
    twoSided
    noShadows
    translucent
    {
        blend add
        map textures/reach/rb_muzzle_flash.tga
        vertexColor
    }
}
'''


PARTICLE = '''particle reach_ar_flash.prt {
    {
        count 1
        material reach/ar_flash
        time 0.055
        cycles 1
        bunching 1
        distribution rect 0 0 0
        direction cone 0
        orientation view
        speed 0
        size 7
        aspect 1
        rotation 0
        randomDistribution 0
        gravity 0
        fadeIn 0
        fadeOut 1
        color 1 1 1 1
    }
}
'''


def counter_material(text):
    for name, parm in [('ones', 10), ('tens', 9)]:
        pattern = re.compile(r'reach/'+name+r'\s*\{(?:[^{}]|\{[^{}]*\})*\}', re.S)
        replacement = '''reach/NAME
{
    twoSided
    translucent
    noShadows
    {
        blend add
        map textures/reach/rb_digits.tga
        translate parmPARM - 0.05, 0
        scale 0.2, 1
    }
}'''.replace('NAME', name).replace('PARM', str(parm))
        text, count = pattern.subn(lambda _: replacement, text)
        if count != 1: raise ValueError('Expected one converted counter material: '+name)
    return text


def package(assets, output):
    assets, output = Path(assets).resolve(), Path(output).resolve()
    if output.exists(): raise FileExistsError('Keep your previous ZIP; choose a new output filename: '+str(output))
    validation = json.loads((assets/'validation-report.json').read_text())
    if validation['clips'] != 25 or validation['framesChecked'] != 844:
        raise ValueError('This rifle requires the validated 25-clip/844-frame conversion')
    entries = {}
    for category in CATEGORIES:
        if not (assets/category).is_dir(): raise ValueError('Missing converted category: '+category)
        for path in sorted((assets/category).rglob('*')):
            if path.is_symlink(): raise ValueError('Do not package linked files: '+str(path))
            if path.is_file():
                relative = path.relative_to(assets).as_posix()
                if ':' in relative or '\\' in relative: raise ValueError('Invalid mod path')
                entries[relative] = path.read_bytes()
    if sum(map(len, entries.values())) > 1024**3: raise ValueError('Converted pack exceeds size limit')
    for needed in ('def/weapon_machinegun.def', 'materials/reach_ar.mtr', 'models/md5/weapons/reach_ar/view.md5mesh'):
        if needed not in entries: raise ValueError('Missing rifle file: '+needed)
    definition = entries['def/weapon_machinegun.def'].decode('utf-8-sig')
    # These use the port's existing weapon event implementations.
    definition = replace_keys(definition, 'weapon_machinegun', {
        'def_melee': 'damage_reach_ar_melee', 'melee_distance': 64,
        'smoke_muzzle': 'reach_ar_flash.prt', 'flashTime': 0.055,
        'reach_has_pose_anims': 0})
    entries['def/weapon_machinegun.def'] = definition.encode()
    entries['def/reach_controls.def'] = (ROOT/'reach_controls.def').read_bytes()
    entries['script/weapon_machinegun.script'] = (ROOT/'reach_machinegun.script').read_bytes()
    entries['script/reach_controls.script'] = (ROOT/'reach_controls.script').read_bytes()
    entries.update(presentation_entries())
    entries['materials/reach_ar.mtr'] = counter_material(entries['materials/reach_ar.mtr'].decode()).encode()
    entries['materials/reach_flash.mtr'] = effect_material().encode()
    entries['particles/reach_ar_flash.prt'] = PARTICLE.encode()
    entries['textures/reach/rb_digits.tga'] = digits()
    entries['textures/reach/rb_muzzle_flash.tga'] = flash()
    entries['autoexec.cfg'] = b'bind SHIFT _speed\nbind V "trigger reach_melee_input"\n'
    if b'getReachPose' in entries['script/weapon_machinegun.script']:
        raise ValueError('Script still requires the custom engine event')
    manifest = {'host': 'released RBDoom3BFG (v1.6.0 source interface checked)',
                'engineRebuilt': False, 'runtimeTest': 'pending', 'clips': 25, 'frames': 844,
                'files': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(entries.items())},
                'limitations': ['Quick grenade inventory integration and full Reach camera behavior pending.',
                                'Counter glyphs and flash texture are reconstructed project assets.',
                                'Melee range is BFG 64 units without a lunge; sprint movement uses BFG run.',
                                'Bloom approximation and rounded BFG damage remain; health/shields are phase 2.']}
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items()): archive.writestr(name, data)
    # Exclusive creation preserves prior packages. An exception removes only our partial ZIP.
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('reach/zzz_reach_ar.pk4', inner.getvalue())
            archive.writestr('reach/reach-package.json', json.dumps(manifest, indent=2)+'\n')
            archive.writestr('Play-Reach.cmd', (ROOT/'Play-Reach.cmd').read_bytes())
            archive.writestr('REACH-README.txt', (ROOT/'README.md').read_bytes())
    except FileExistsError:
        raise
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', nargs='?', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out is None:
        args.out = Path.cwd()/'Reach-RBDoom3BFG.zip'
        index = 2
        while args.out.exists():
            args.out = Path.cwd()/('Reach-RBDoom3BFG-'+str(index)+'.zip')
            index += 1
    assets = args.assets
    if assets is None:
        pointer = Path.cwd()/'reach-weapon-data.path'
        if not pointer.is_file(): raise ValueError('Extract these tools beside reach-weapon-data.path, or drag your converted folder onto Build-Reach-RBDoom.cmd.')
        value = pointer.read_text(encoding='utf-8-sig').strip()
        if not value: raise ValueError('The converted folder pointer is empty')
        assets = Path(value)
    package(assets, args.out)
    print('Created:', args.out.resolve())
    print('Extract this private ZIP into your released RBDoom3BFG folder, then double-click Play-Reach.cmd.')


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print('Package failed:', error, file=sys.stderr)
        sys.exit(1)
