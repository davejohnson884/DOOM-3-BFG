"""Check contracts with the pinned host, accepted pose and final packaged script."""
import io
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from build_combat import overlay, script


def check(source):
    source = Path(source)
    text = script().decode()
    events = set()
    for file in (source/'neo/d3xp').rglob('*.cpp'):
        events.update(re.findall(r'\bidEventDef\s+\w+\s*\(\s*"([^"\n]+)"',file.read_text(errors='replace')))
    variables = set(re.findall(r'\b(?:float|vector|entity|boolean|string)\s+(\w+)\s*;', text))
    assert not variables & events, 'Script local shadows a native event: '+str(variables & events)
    declarations = re.findall(r'^scriptEvent float (\w+)\(\);',text,re.M)
    assert set(declarations) == {'reachGrenadesAvailable','reachThrowFrag','reachQuickAction'}
    assert set(declarations) <= events, 'Native event implementation missing'
    methods = re.findall(r'(?:void|float) weapon_machinegun::(\w+)\(',text)
    assert len(methods) == len(set(methods)), 'Duplicate script functions'
    assert 'ReachInstallControls' not in text
    assert 'sys.spawn("reach_input' not in text
    assert text.count('melee();') == 1 and text.count('reachThrowFrag()') == 2
    with zipfile.ZipFile(io.BytesIO(overlay())) as archive:
        assert archive.read('script/weapon_machinegun.script') == script()
        controls = archive.read('reach_controls.cfg').decode()
        assert 'bind V _impulse23' in controls
        assert 'bind G _impulse24' in controls
        assert 'reach_meleeRequest' not in text and 'reach_grenadeRequest' not in text
        assert 'trigger ' not in controls
        assert 'r_reachWeaponFov' not in controls and 'g_fov' not in controls
    files = set(subprocess.check_output(['git','diff','--name-only'],cwd=source,text=True).splitlines())
    assert files == {'neo/renderer/RenderCommon.h','neo/renderer/tr_frontend_addmodels.cpp',
                     'neo/renderer/RenderBackend.cpp','neo/d3xp/Weapon.cpp','neo/d3xp/Weapon.h','neo/d3xp/Projectile.cpp'}, files
    print('PASS: native/script events, event-name collision check, packaged V/G bindings, '
          'unchanged r12 pose, and six-file source scope. Actual in-game playtest still required.')


if __name__ == '__main__': check(sys.argv[1])
