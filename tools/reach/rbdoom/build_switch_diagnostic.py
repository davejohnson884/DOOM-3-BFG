"""Build a script-only update; no donor assets or engine executable."""
import argparse
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = {
    'script/weapon_machinegun.script': 'reach_machinegun.script',
    'script/reach_controls.script': 'reach_controls.script',
    'def/reach_controls.def': 'reach_controls.def',
}


def build(output):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w', zipfile.ZIP_DEFLATED) as archive:
        for target, source in PAYLOAD.items():
            archive.writestr(target, (ROOT/source).read_bytes())
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('reach/zzzz_reach_switch.pk4', inner.getvalue())
        archive.writestr('Play-Reach-diagnostic.cmd', (ROOT/'Play-Reach-diagnostic.cmd').read_bytes())
        archive.writestr('REACH-SWITCH-DIAGNOSTIC.txt', (ROOT/'SWITCH-DIAGNOSTIC.txt').read_bytes())
        archive.writestr('PROJECT-GPL.txt', (ROOT.parents[2]/'COPYING.txt').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
