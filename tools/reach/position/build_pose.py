"""Package rifle-only angle controls on the accepted projection and r9 pose."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

from build_position import DECLARATION, DECL_PATH, OFFSET, PK4_PATH, ROOT, REPO
from build_candidate import overlay as projection_overlay, script as projection_script

PATTERN = r'void weapon_machinegun::ReachApplyViewPose\(\)\s*\{.*?\n\}'
SCRIPT_PATH = 'script/weapon_machinegun.script'


def script():
    source = projection_script().decode()
    body = (ROOT / 'reach_pose.script').read_text().strip()
    result, count = re.subn(PATTERN, lambda _: body, source, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one existing presentation method')
    return result.encode()


def build(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Keep the previous package; choose a new output name')
    with zipfile.ZipFile(io.BytesIO(projection_overlay())) as archive:
        baseline = {name: archive.read(name) for name in archive.namelist()}
    # The same virtual filenames avoid duplicate declarations or script objects.
    changes = {DECL_PATH: DECLARATION, SCRIPT_PATH: script()}
    combined = baseline | changes
    if set(name for name in combined if combined[name] != baseline[name]) != set(changes):
        raise ValueError('Unexpected changes outside the rifle presentation')
    # All weapon state bodies and object fields stay byte-for-byte unchanged.
    if re.sub(PATTERN, '', changes[SCRIPT_PATH].decode(), flags=re.S) != re.sub(
            PATTERN, '', baseline[SCRIPT_PATH].decode(), flags=re.S):
        raise ValueError('Unexpected weapon logic or object layout changes')
    pk4 = io.BytesIO()
    with zipfile.ZipFile(pk4, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(changes.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(io.BytesIO(pk4.getvalue())) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(changes):
            raise ValueError('Invalid pose overlay')
    files = {
        PK4_PATH: pk4.getvalue(),
        'REACH-POSE-README.txt': (ROOT / 'POSE-README.txt').read_bytes(),
    }
    report = {
        'revision': 'r10',
        'toolCommit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'requires': 'Installed r8 projection candidate and existing private Reach assets',
        'modelOffset': OFFSET,
        'positionRelativeToR9': [0, 0, 0],
        'defaultAnglesDegrees': [0, 0, -3],
        'rotationPivotModelSpace': [15.84341446, -4.47929218, 0.28925242],
        'controls': ['reach_arPitch', 'reach_arYaw', 'reach_arRoll'],
        'calibration': 'Small roll trial; not a recovered Reach retail pose',
        'projectionChanged': False,
        'executableChanged': False,
        'globalGunSettingsChanged': False,
        'changedFromR9': [SCRIPT_PATH],
        'runtimeTest': 'Not run in cloud; owner comparison required',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }
    files['reach-pose-build.json'] = json.dumps(report, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Package CRC verification failed')
    print(json.dumps({'package': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'changedFromR9': report['changedFromR9']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
