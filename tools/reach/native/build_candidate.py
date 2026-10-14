"""Package a separate RBDoom projection candidate without donor assets."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RBDOOM = ROOT.parent/'rbdoom'
sys.path.insert(0, str(RBDOOM))
from presentation import entries as presentation_entries
from apply_rbdoom import UPSTREAM


def script():
    text = (RBDOOM/'reach_machinegun.script').read_text()
    pattern = r'void weapon_machinegun::ReachApplyViewPose\(\)\s*\{.*?\n\}'
    body = '''void weapon_machinegun::ReachApplyViewPose() {
    float reach_root_joint;
    // Parm 6 is reserved by this candidate for the owned Reach projection.
    // Counter UV controls remain in parms 9 and 10.
    setShaderParm(6, 1);
    reach_root_joint = getJointHandle("origin");
    if (reach_root_joint >= 0) {
        // Remove r7's added rotation and retain the original animated root.
        setJointAngle(reach_root_joint, JOINTMOD_NONE, '0 0 0');
    }
    ReachTrace("projection tagged; offset=(-3 0 -1.2); r_reachWeaponFov=" + sys.getcvar("r_reachWeaponFov"));
    if (sys.getcvar("g_debugWeapon") == "1") {
        ReachTrace("world camera: g_fov=" + sys.getcvar("g_fov") + " g_gunScale=" + sys.getcvar("g_gunScale"));
        ReachTrace("host gun position: X=" + sys.getcvar("g_gunX") + " Y=" + sys.getcvar("g_gunY") + " Z=" + sys.getcvar("g_gunZ"));
    }
}'''
    text, count = re.subn(pattern, lambda _: body, text, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one existing presentation method')
    return text.replace('[ReachSwitch r7]', '[ReachProjection r8]').encode()


def overlay():
    entries = presentation_entries()
    entries['def/reach_presentation.def'] = b'''model viewmodel_reach_ar_present {
    inherit viewmodel_reach_ar
    offset ( -3 0 -1.2 )
}
'''
    entries['script/weapon_machinegun.script'] = script()
    entries['script/reach_controls.script'] = (RBDOOM/'reach_controls.script').read_bytes()
    entries['def/reach_controls.def'] = (RBDOOM/'reach_controls.def').read_bytes()
    entries['reach_projection.cfg'] = b'exec reach_controls.cfg\nset r_reachWeaponFov 54\n'
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()): archive.writestr(name, data)
    return result.getvalue()


def launcher(diagnostic=False):
    path = RBDOOM/('Play-Reach-diagnostic.cmd' if diagnostic else 'Play-Reach.cmd')
    text = path.read_text().replace('RBDoom3BFG.exe', 'ReachRBDoom3BFG.exe')
    text = text.replace('+exec reach_controls.cfg', '+exec reach_projection.cfg')
    if diagnostic:
        text = text.replace('reach\\zzzz_reach_switch.pk4', 'reach\\zzzzz_reach_projection.pk4')
        text = text.replace('Extract the complete Reach switch diagnostic ZIP here.', 'Extract the complete projection candidate ZIP here.')
    return text.replace('\n', '\r\n').encode()


def check_pe64(path):
    data = Path(path).read_bytes()
    if len(data) < 128 or data[:2] != b'MZ': raise ValueError('Expected a Windows executable')
    offset = struct.unpack_from('<I', data, 60)[0]
    if offset + 26 > len(data) or data[offset:offset+4] != b'PE\0\0':
        raise ValueError('Invalid Windows executable header')
    machine = struct.unpack_from('<H', data, offset+4)[0]
    magic = struct.unpack_from('<H', data, offset+24)[0]
    if machine != 0x8664 or magic != 0x20b: raise ValueError('The candidate requires Win64, not Win32')
    return data


def build(output, engine, capture, source):
    output, source = Path(output), Path(source).resolve()
    if output.exists(): raise FileExistsError('Keep the previous package; choose a new output name')
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=source, text=True).strip()
    if head != UPSTREAM: raise ValueError('Wrong RBDoom source revision')
    changed_sources = ['neo/renderer/RenderCommon.h', 'neo/renderer/tr_frontend_addmodels.cpp',
                       'neo/renderer/RenderBackend.cpp', 'neo/d3xp/Weapon.cpp']
    for name in changed_sources:
        if 'Reach opt-in weapon projection' not in (source/name).read_text(encoding='utf-8-sig'):
            raise ValueError('Source is missing the extension: '+name)
    entries = {
        'ReachRBDoom3BFG.exe': check_pe64(engine),
        'ReachDebugLog.exe': Path(capture).read_bytes(),
        'reach/zzzzz_reach_projection.pk4': overlay(),
        'Play-Reach-projection.cmd': launcher(),
        'Play-Reach-projection-diagnostic.cmd': launcher(True),
        'REACH-PROJECTION-README.txt': (ROOT/'PLAYER-README.txt').read_bytes(),
        'licenses/Project-GPL.txt': (REPO/'COPYING.txt').read_bytes(),
        'licenses/RBDoom-GPL.md': (source/'LICENSE.md').read_bytes(),
        'licenses/RBDoom-exceptions.md': (source/'LICENSE_EXCEPTIONS.md').read_bytes(),
        'source/ReachDebugLog.cs': (RBDOOM/'ReachDebugLog.cs').read_bytes(),
    }
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in {'.py','.h','.cpp','.json','.ps1','.md','.txt'}:
            entries['source/native/'+path.name] = path.read_bytes()
    patch = subprocess.check_output(['git','diff','--binary','--',*changed_sources], cwd=source)
    entries['source/RBDoom-projection.patch'] = patch
    entries['source/ReachWeaponProjection.h'] = (ROOT/'WeaponProjection.h').read_bytes()
    tool_commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip()
    report = {
        'upstreamCommit': UPSTREAM, 'toolCommit': tool_commit,
        'runtimeTest': 'not run in cloud; owner playtest required',
        'referenceWeaponFovHorizontal4By3': 54,
        'worldFovChanged': False, 'threadSettingsChanged': False,
        'sourceFiles': {p: hashlib.sha256((source/p).read_bytes()).hexdigest() for p in changed_sources},
        'files': {p: hashlib.sha256(b).hexdigest() for p,b in sorted(entries.items())},
    }
    entries['reach-projection-build.json'] = json.dumps(report, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(entries.items()): archive.writestr(name,data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None: raise ValueError('Package CRC verification failed')
    print(json.dumps({'package':str(output),'bytes':output.stat().st_size,
                      'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                      'upstreamCommit':UPSTREAM, 'runtimeTest':report['runtimeTest']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    build(args.output, args.engine, args.capture, args.source)
