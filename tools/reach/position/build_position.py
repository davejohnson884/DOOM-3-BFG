"""Package a declaration-only pose update for the accepted r8 projection."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT.parent / 'native'))
from build_candidate import overlay as projection_overlay

# +X forward, +Y left, +Z up. Relative to r8, move the complete rig
# 7 units away from the camera, 4.2 right and 1.6 down. No rotation/scale.
OFFSET = (4, -4.2, -2.8)
DECLARATION = '''model viewmodel_reach_ar_present {
    inherit viewmodel_reach_ar
    offset ( 4 -4.2 -2.8 )
}
'''.encode()
PK4_PATH = 'reach/zzzzzz_reach_position.pk4'
DECL_PATH = 'def/reach_presentation.def'


def build(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Keep the previous package; choose a new output name')

    # Use the same virtual filename, so PK4 precedence replaces the declaration
    # instead of introducing a duplicate model declaration in a different file.
    with zipfile.ZipFile(io.BytesIO(projection_overlay())) as baseline:
        if b'offset ( -3 0 -1.2 )' not in baseline.read(DECL_PATH):
            raise ValueError('This update was calibrated relative to r8')
        previous = {name: baseline.read(name) for name in baseline.namelist()}
    pk4 = io.BytesIO()
    with zipfile.ZipFile(pk4, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DECL_PATH, DECLARATION)
    with zipfile.ZipFile(io.BytesIO(pk4.getvalue())) as archive:
        if archive.namelist() != [DECL_PATH] or archive.testzip() is not None:
            raise ValueError('Expected exactly one valid model declaration')
        combined = previous | {name: archive.read(name) for name in archive.namelist()}
    if [name for name in combined if combined[name] != previous[name]] != [DECL_PATH]:
        raise ValueError('The update must change only the pose declaration')

    files = {
        PK4_PATH: pk4.getvalue(),
        'REACH-POSITION-README.txt': (ROOT / 'PLAYER-README.txt').read_bytes(),
    }
    report = {
        'revision': 'r9',
        'toolCommit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'requires': 'Installed r8 projection candidate and existing private Reach assets',
        'modelOffset': OFFSET,
        'translationFromR8': [7, -4.2, -1.6],
        'calibration': 'Approximate fit to owner screenshot and full-frame Reach 360 reference; saved gun offsets not yet measured',
        'projectionChanged': False,
        'executableChanged': False,
        'changedVirtualFiles': [DECL_PATH],
        'runtimeTest': 'Not run in cloud; owner comparison required',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }
    files['reach-position-build.json'] = json.dumps(report, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Package CRC verification failed')
    print(json.dumps({'package': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'changedVirtualFiles': report['changedVirtualFiles']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
