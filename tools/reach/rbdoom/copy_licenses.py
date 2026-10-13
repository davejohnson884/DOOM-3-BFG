import importlib.metadata
import shutil
import sys
from pathlib import Path

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
dist = importlib.metadata.distribution('pyinstaller')
copied = 0
for item in dist.files or []:
    if 'license' in str(item).lower() and '.dist-info' in str(item):
        source = Path(dist.locate_file(item))
        if source.is_file():
            shutil.copyfile(source, output/('PyInstaller-'+item.name))
            copied += 1
if not copied: raise RuntimeError('Missing PyInstaller license text')
for candidate in (Path(sys.base_prefix)/'LICENSE.txt', Path(sys.base_prefix)/'LICENSE'):
    if candidate.is_file():
        shutil.copyfile(candidate, output/'Python.txt')
        break
else: raise RuntimeError('Missing Python runtime license text')
