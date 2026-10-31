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
        assert 'bind V reachMelee' in controls
        assert 'bind G reachGrenade' in controls
        assert 'reach_meleeRequest' not in text and 'reach_grenadeRequest' not in text
        assert 'trigger ' not in controls
        assert 'r_reachWeaponFov' not in controls and 'g_fov' not in controls
    files = set(subprocess.check_output(['git','diff','--name-only'],cwd=source,text=True).splitlines())
    assert files == {'neo/renderer/RenderCommon.h','neo/renderer/tr_frontend_addmodels.cpp',
                     'neo/renderer/RenderBackend.cpp','neo/renderer/ModelManager.cpp','neo/d3xp/Weapon.cpp','neo/d3xp/Weapon.h','neo/d3xp/Projectile.cpp','neo/d3xp/gamesys/SysCmds.cpp','neo/d3xp/Player.cpp','neo/d3xp/SmokeParticles.cpp'}, files
    original_models = subprocess.check_output(['git','show','HEAD:neo/renderer/ModelManager.cpp'],cwd=source,text=True)
    patched_models = (source/'neo/renderer/ModelManager.cpp').read_text()
    patched_models = patched_models.replace('#include "ReachSpartanModelAliases.h"\n','')
    model_start=patched_models.index('    // Reach opt-in weapon projection / compatible saved Spartan player models.')
    model_end=patched_models.index('\n\tidStrStatic< MAX_OSPATH > extension;',model_start)
    model_insertion=patched_models[model_start:model_end]
    assert 'GetCVarString("fs_game"), "reach"' in model_insertion
    assert 'fileSystem->ReadFile(replacement, NULL, NULL) >= 0' in model_insertion
    assert 'ReachSpartan::Replacement' in model_insertion
    assert patched_models[:model_start]+patched_models[model_end:]==original_models
    # Removing the guarded insertion must reproduce every byte of the stock
    # player implementation: all other weapons retain the supported host path.
    original_player = subprocess.check_output(['git','show','HEAD:neo/d3xp/Player.cpp'],cwd=source,text=True)
    patched_player = (source/'neo/d3xp/Player.cpp').read_text()
    camera_start=patched_player.index('        // Reach opt-in weapon projection / animation camera.')
    camera_end=patched_player.index('        // Reach animation camera end.\n',camera_start)+len('        // Reach animation camera end.\n')
    camera_insertion=patched_player[camera_start:camera_end]
    assert 'ReachCameraMotion' in camera_insertion and 'viewAngles =' not in camera_insertion
    for guard in ['!common->IsMultiplayer()', '!spectating', '!gameLocal.inCinematic', 'privateCameraView==NULL', 'gameLocal.GetCamera()==NULL', '!pm_thirdPerson.GetBool()']:
        assert guard in camera_insertion
    patched_player=patched_player[:camera_start]+patched_player[camera_end:]
    start = patched_player.index('\t// Reach opt-in weapon projection / authored first-person movement.')
    end = patched_player.index('\tidVec3\tgunOfs = GunAcceleratingOffset();', start)
    insertion = patched_player[start:end]
    assert patched_player[:start] + patched_player[end:] == original_player
    for guard in ['!common->IsMultiplayer()', 'reach_authored_motion', 'viewmodel_reach_ar', 'weapon_machinegun']:
        assert guard in insertion
    assert 'physicsObj.HasGroundContacts() ? 1 : -1' in insertion
    commands=(source/'neo/d3xp/gamesys/SysCmds.cpp').read_text()
    for name in ['reachMelee','reachGrenade']:
        assert re.search(r'AddCommand\( "'+name+r'", \w+, CMD_FL_GAME,',commands), 'Command must not require cheats'
    print('PASS: native/script events, event-name collision check, packaged V/G bindings, '
          'unchanged r12 pose, non-cheat commands, ten-file scope, guarded saved-player mesh mapping and unchanged non-Reach player path. Actual in-game playtest still required.')


if __name__ == '__main__': check(sys.argv[1])



