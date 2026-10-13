"""Include license texts for the bundled Python libraries/runtime."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

output = Path(sys.argv[1]); output.mkdir(parents=True, exist_ok=True)
for name in ('numpy', 'Pillow', 'pyinstaller'):
    dist = importlib.metadata.distribution(name)
    for item in dist.files or []:
        if 'license' in item.name.lower() and '.dist-info' in str(item):
            source = Path(dist.locate_file(item))
            if source.is_file(): shutil.copyfile(source, output/(name+'-'+item.name))
for candidate in (Path(sys.base_prefix)/'LICENSE.txt', Path(sys.base_prefix)/'LICENSE'):
    if candidate.is_file(): shutil.copyfile(candidate, output/'Python.txt'); break
