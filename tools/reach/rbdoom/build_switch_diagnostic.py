"""Build a script-only update; no donor assets or engine executable."""
import argparse
import io
import zipfile
from pathlib import Path
from presentation import entries as presentation_entries

ROOT = Path(__file__).resolve().parent
PAYLOAD = {
    'script/weapon_machinegun.script': 'reach_machinegun.script',
    'script/reach_controls.script': 'reach_controls.script',
    'def/reach_controls.def': 'reach_controls.def',
}


def build(output, capture_exe):
    capture_exe = Path(capture_exe)
    capture_data = capture_exe.read_bytes()
    if not capture_data.startswith(b'MZ'):
        raise ValueError('Expected the built Windows debug-output capture executable')
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w', zipfile.ZIP_DEFLATED) as archive:
        for target, source in PAYLOAD.items():
            archive.writestr(target, (ROOT/source).read_bytes())
        for target, data in presentation_entries().items():
            archive.writestr(target, data)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('reach/zzzz_reach_switch.pk4', inner.getvalue())
        archive.writestr('Play-Reach-diagnostic.cmd', (ROOT/'Play-Reach-diagnostic.cmd').read_bytes())
        archive.writestr('REACH-SWITCH-DIAGNOSTIC.txt', (ROOT/'SWITCH-DIAGNOSTIC.txt').read_bytes())
        archive.writestr('PROJECT-GPL.txt', (ROOT.parents[2]/'COPYING.txt').read_bytes())
        archive.writestr('ReachDebugLog.exe', capture_data)
        archive.writestr('ReachDebugLog.cs', (ROOT/'ReachDebugLog.cs').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--capture-exe', type=Path, required=True)
    args = parser.parse_args()
    build(args.output, args.capture_exe)
