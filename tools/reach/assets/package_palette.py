"""Package a complete, matched self-contained collector; never a DLL add-on."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

REQUIRED = {
    'ReachAssetExport.exe', 'ReachAssetExport.dll',
    'ReachAssetExport.deps.json', 'ReachAssetExport.runtimeconfig.json',
    'TagTool.dll', 'Reclaimer.Blam.dll', 'Tools/fmod.dll',
    'coreclr.dll', 'hostfxr.dll', 'hostpolicy.dll', 'System.Private.CoreLib.dll',
    'schemas/matg.xml', 'Collect-Reach-palette.cmd', 'PALETTE.txt',
    'licenses/Reclaimer.txt', 'licenses/TagTool.txt', 'licenses/Assembly.txt',
}


def package(published, output):
    published, output = Path(published).resolve(), Path(output)
    if output.exists():
        raise FileExistsError('Preserve the previous ZIP; use a new output path')
    files = {}
    for path in sorted(published.rglob('*')):
        if path.is_symlink():
            raise ValueError('Do not package linked files: '+str(path))
        if path.is_file():
            files[path.relative_to(published).as_posix()] = path
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError('Incomplete standalone collector: '+', '.join(sorted(missing)))
    report = {
        'package': 'Reach-palette-tools',
        'deployment': 'Complete matched publish output; extract to a new empty folder',
        'sourceCommit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[3], text=True).strip(),
        'runtimeValidation': 'Final ZIP must pass verify_palette_package.py before upload',
        'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, name)
        archive.writestr('reach-palette-tool-build.json', json.dumps(report, indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Packaged collector ZIP failed CRC verification')
    print(json.dumps({'path': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'files': len(files)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('published', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.published, args.output)
