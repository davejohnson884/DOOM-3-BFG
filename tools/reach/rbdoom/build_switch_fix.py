"""Build the drop-in controller spawn fix without assets or executables."""
import argparse
import io
import zipfile
from pathlib import Path

from build_switch_diagnostic import ROOT, PAYLOAD
from presentation import entries as presentation_entries


def build(output):
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
        archive.writestr('REACH-SWITCH-FIX.txt', (ROOT/'SWITCH-FIX.txt').read_bytes())
        archive.writestr('PROJECT-GPL.txt', (ROOT.parents[2]/'COPYING.txt').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
