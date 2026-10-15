"""Package the owner's gun settings with launchers that load them automatically."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

from build_pose import script, SCRIPT_PATH
from build_position import ROOT, REPO, DECL_PATH, DECLARATION, OFFSET, PK4_PATH
from build_candidate import launcher as projection_launcher

CONFIG_PATH = 'reach/reach_pose.cfg'


def launcher(diagnostic=False):
    text = projection_launcher(diagnostic).decode().replace('\r\n', '\n')
    if text.count('+exec reach_projection.cfg') != 1:
        raise ValueError('Expected one projection config command')
    text = text.replace('+exec reach_projection.cfg', '+exec reach_pose.cfg')
    guard = '''if not exist "%~dp0reach\\reach_pose.cfg" (
  echo Extract the complete r11 ZIP here, including reach\\reach_pose.cfg.
  pause
  exit /b 1
)
if not exist "%~dp0reach\\zzzzzz_reach_position.pk4" (
  echo Extract the complete r11 ZIP here, including the position PK4.
  pause
  exit /b 1
)
'''
    anchor = 'if not exist "%~dp0reach\\zzz_reach_ar.pk4" ('
    if text.count(anchor) != 1:
        raise ValueError('Expected the existing asset guard')
    text = text.replace(anchor, guard + anchor)
    return text.replace('\n', '\r\n').encode()


def build(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Keep the previous package; choose a new output name')
    # Game script and declaration are identical to r10. Only startup loading
    # changes; there is no new script checksum or rotation trial in this update.
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DECL_PATH, DECLARATION)
        archive.writestr(SCRIPT_PATH, script())
    files = {
        PK4_PATH: inner.getvalue(),
        CONFIG_PATH: (ROOT / 'reach_pose.cfg').read_bytes(),
        'Play-Reach-projection.cmd': launcher(),
        'Play-Reach-projection-diagnostic.cmd': launcher(True),
        'REACH-PRESET-README.txt': (ROOT / 'PRESET-README.txt').read_bytes(),
    }
    report = {
        'revision': 'r11',
        'toolCommit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'requires': 'Installed r8 projection candidate and existing private Reach assets',
        'modelOffset': OFFSET,
        'gunSettings': {'g_gunX': -4, 'g_gunY': 4, 'g_gunZ': 1},
        'angleSettings': {'reach_arPitch': 0, 'reach_arYaw': 0, 'reach_arRoll': -3},
        'config': CONFIG_PATH,
        'scriptChangedFromR10': False,
        'projectionChanged': False,
        'executableChanged': False,
        'runtimeTest': 'Not run in cloud; Windows CMD/config fixture tested separately',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }
    files['reach-preset-build.json'] = json.dumps(report, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Package CRC verification failed')
    print(json.dumps({'package': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'gunSettings': report['gunSettings']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
