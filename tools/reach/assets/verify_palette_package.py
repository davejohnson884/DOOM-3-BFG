"""Run the actual shipped Windows collector from an isolated extracted ZIP."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


def verify(package):
    with tempfile.TemporaryDirectory(prefix='Reach Palette Clean Install ') as temp:
        root = Path(temp); installed = root/'New Collector Folder'
        with zipfile.ZipFile(package) as archive:
            for name in archive.namelist():
                path = PurePosixPath(name.replace('\\', '/'))
                if path.is_absolute() or '..' in path.parts or ':' in name:
                    raise ValueError('Unsafe package path: '+name)
            archive.extractall(installed)
        report = json.loads((installed/'reach-palette-tool-build.json').read_text())
        for name, expected in report['files'].items():
            if hashlib.sha256((installed/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Final ZIP payload mismatch: '+name)
        unrelated = root/'Unrelated Working Directory'; unrelated.mkdir()
        tool = installed/'ReachAssetExport.exe'
        result = subprocess.run([str(tool), '--selftest'], cwd=unrelated,
                                capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError('Packaged runtime selftest failed:\n'+result.stdout+'\n'+result.stderr)
        # Exercise the palette entry path too. A missing map must produce the
        # controlled file error, rather than the owner's pre-Main DLL failure.
        missing = subprocess.run([str(tool), '--mcc', str(root/'Missing MCC Install'),
                                  '--out', str(root/'Collection Output'), '--palette'],
                                 cwd=unrelated, capture_output=True, text=True, timeout=60)
        if missing.returncode != 1 or 'forge_halo.map was not found' not in missing.stderr:
            raise RuntimeError('Palette entry-point validation failed:\n'+missing.stdout+'\n'+missing.stderr)
        if list(root.rglob('reach-palette-*.zip')):
            raise ValueError('A failed palette read produced a misleading result ZIP')
        print('PASS: final ZIP loads matched TagTool/native/runtime libraries from a fresh '
              'folder with spaces, passes actual selftests, and reaches controlled palette input validation.')


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
