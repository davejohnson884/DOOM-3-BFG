import io
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from test_package import PackageChecks

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    assets = PackageChecks().assets(root)
    output = root/'mod.zip'
    result = subprocess.run([sys.argv[1], str(assets), '--out', str(output)], capture_output=True, text=True)
    if result.returncode: raise RuntimeError(result.stdout+'\n'+result.stderr)
    with zipfile.ZipFile(output) as outer:
        assert outer.testzip() is None
        with zipfile.ZipFile(io.BytesIO(outer.read('reach/zzz_reach_ar.pk4'))) as inner:
            assert inner.testzip() is None
            assert b'getReachPose' not in inner.read('script/weapon_machinegun.script')
            assert 'script/reach_controls.script' in inner.namelist()
            assert 'materials/reach_flash.mtr' in inner.namelist()
            assert 'def/reach_presentation.def' in inner.namelist()
            assert 'skins/reach_presentation.skin' in inner.namelist()
            assert 'materials/reach_presentation.mtr' in inner.namelist()
    print('PASS: frozen executable created complete drop-in archive with bundled script templates and effects')
