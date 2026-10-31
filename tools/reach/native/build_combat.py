"""Build an asset-free r15 repair bundle around the accepted r12 pose."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'position'))
from build_preset import script as pose_script, launcher as pose_launcher, CONFIG_PATH
from build_position import DECL_PATH, DECLARATION, REPO

PK4_PATH = 'reach/zzzzzzzzz_reach_input.pk4'
CONTROLS = b'bind SHIFT _speed\nbind V reachMelee\nbind G reachGrenade\necho "Reach r15 gameplay V/G bindings loaded"\nbind V\nbind G\n'


def launcher(diagnostic=False):
    text = pose_launcher(diagnostic).decode().replace('\r\n','\n')
    text = text.replace('+exec reach_pose.cfg','+exec reach_pose.cfg +exec reach_controls_r15.cfg')
    guard = '''if not exist "%~dp0reach\\zzzzzzzzz_reach_input.pk4" (
  echo Extract the complete r15 ZIP here, including the input PK4.
  pause
  exit /b 1
)
if not exist "%~dp0reach\\reach_controls_r15.cfg" (
  echo Extract the complete r15 ZIP here, including reach_controls_r15.cfg.
  pause
  exit /b 1
)
if not exist "%~dp0reach\\zzzzzzzzzzz_reach_repair_r15.pk4" (
  echo Run Apply-Reach-repair.cmd once before starting this update.
  pause
  exit /b 1
)
'''
    text = text.replace('if not exist "%~dp0reach\\reach_pose.cfg" (',guard+'if not exist "%~dp0reach\\reach_pose.cfg" (',1)
    return text.replace('\n','\r\n').encode()


def script():
    text = pose_script().decode()
    text = text.replace('#include "script/reach_controls.script"', '''// These events require the Reach executable.
scriptEvent float reachGrenadesAvailable();
scriptEvent float reachThrowFrag();
scriptEvent float reachQuickAction();''')
    text = text.replace('    ReachTrace("constructor entered");',
                        '    sys.println("[Reach r15] gameplay-input rifle script active");\n    ReachTrace("constructor entered");')
    text = text.replace('    float reach_pending_melee;', '    float reach_pending_melee;\n    float reach_pending_grenade;')
    text = text.replace('    void ReachInstallControls();', '    void ReachReadInput();\n    void ReachClearInput();\n    void Grenade();')
    start = text.index('void weapon_machinegun::ReachInstallControls()')
    end = text.index('void weapon_machinegun::RecoverBloom()', start)
    text = text[:start] + (ROOT/'reach_input.script').read_text() + '\n' + text[end:]
    start = text.index('    if (!reach_controls_ready) {')
    end = text.index('    while (1) {', start)
    text = text[:start] + text[end:]
    text = text.replace('    reach_controls_ready = false;','    reach_pending_grenade = 0;\n    ReachClearInput();')
    text = text.replace('    boolean reach_controls_ready;\n', '')
    text = text.replace('    ReachApplyViewPose();\n    weaponRising();',
                        '    ReachApplyViewPose();\n    reach_action_locked = 0;\n    reach_pending_melee = 0;\n    reach_pending_grenade = 0;\n    ReachClearInput();\n    weaponRising();')
    text = text.replace('    weaponLowering();', '    reach_action_locked = 1;\n    reach_pending_melee = 0;\n    reach_pending_grenade = 0;\n    ReachClearInput();\n    weaponLowering();')
    text = text.replace('    ReachTrace("raise animation completed; requesting Idle");', '    ReachClearInput();\n    ReachTrace("raise animation completed; requesting Idle");')
    text = text.replace('if (ReachPose() == 2) { weaponState("Quick", 1); }',
                        'if (ReachPose() == 2) { weaponState("Quick", 1); }\n    if (ReachPose() == 3) { weaponState("Grenade", 1); }')
    text = text.replace('    if (reach_pending_melee) { return 2; }',
                        '    ReachReadInput();\n    if (reach_pending_melee) { return 2; }\n    if (reach_pending_grenade) { return 3; }')
    text = text.replace('    reach_hit_done = false;',
                        '    reach_pending_grenade = 0;\n    ReachClearInput();\n    reach_hit_done = false;')
    text = text.replace('    while (sys.getTime() < reach_done_time) {',
                        '    while (sys.getTime() < reach_done_time) {\n        ReachReadInput();')
    text = text.replace('void weapon_machinegun::EnterCinematic() {',
                        'void weapon_machinegun::EnterCinematic() {\n    reach_pending_grenade = 0;\n    ReachClearInput();')
    text = text.replace('void weapon_machinegun::ExitCinematic() {',
                        'void weapon_machinegun::ExitCinematic() {\n    reach_pending_grenade = 0;\n    ReachClearInput();')
    text += '\n' + (ROOT/'reach_grenade.script').read_text()
    # The accepted projection/placement method must remain byte-for-byte.
    pattern = r'void weapon_machinegun::ReachApplyViewPose\(\).*?\n\}'
    if re.search(pattern, text, re.S)[0] != re.search(pattern, pose_script().decode(), re.S)[0]:
        raise ValueError('Combat update changed the accepted pose')
    if 'trigger reach_melee_input' in text or 'ReachInstallControls' in text:
        raise ValueError('Old cheat-protected input path remains')
    return re.sub(r'\[Reach(?:Switch|Projection) r\d+\]', '[ReachCombat r15]', text).encode()


def overlay():
    entries = {
        DECL_PATH: DECLARATION,
        'script/weapon_machinegun.script': script(),
        'def/reach_frag.def': (ROOT/'reach_frag.def').read_bytes(),
        'reach_controls.cfg': CONTROLS,
        'reach_controls_r15.cfg': CONTROLS,
    }
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()): archive.writestr(name, data)
    return result.getvalue()


def build(output, engine, capture, source, repair):
    import build_candidate as candidate
    output = Path(output)
    if output.exists(): raise FileExistsError(output)
    files = {
        'ReachRBDoom3BFG.exe': candidate.check_pe64(engine),
        'ReachDebugLog.exe': Path(capture).read_bytes(),
        'ReachRepair.exe': candidate.check_pe64(repair),
        'Apply-Reach-repair.cmd': (ROOT/'Apply-Reach-repair.cmd').read_bytes(),
        # New name proves that the input update was copied and outranks r12/r13.
        PK4_PATH: overlay(), CONFIG_PATH: (ROOT.parent/'position/reach_pose.cfg').read_bytes(),
        'reach/reach_controls_r15.cfg': CONTROLS,
        'Play-Reach-projection.cmd': launcher(),
        'Play-Reach-projection-diagnostic.cmd': launcher(True),
        'REACH-REPAIR-R15.txt': (ROOT/'COMBAT-R15.txt').read_bytes(),
        'licenses/Project-GPL.txt': (REPO/'COPYING.txt').read_bytes(),
        'licenses/RBDoom-GPL.md': (Path(source)/'LICENSE.md').read_bytes(),
        'licenses/RBDoom-exceptions.md': (Path(source)/'LICENSE_EXCEPTIONS.md').read_bytes(),
    }
    license_dir = ROOT.parent.parent.parent/'build/repair-licenses'
    subprocess.run([sys.executable, str(ROOT.parent/'rbdoom/copy_licenses.py'), str(license_dir)], check=True)
    for path in license_dir.iterdir():
        if path.is_file(): files['licenses/repair/'+path.name] = path.read_bytes()
    for directory in [ROOT, ROOT.parent/'position']:
        for path in directory.iterdir():
            if path.is_file(): files['source/'+directory.name+'/'+path.name] = path.read_bytes()
    paths = ['neo/renderer/RenderCommon.h','neo/renderer/tr_frontend_addmodels.cpp',
             'neo/renderer/RenderBackend.cpp','neo/renderer/ModelManager.cpp','neo/d3xp/Weapon.cpp','neo/d3xp/Weapon.h','neo/d3xp/Projectile.cpp','neo/d3xp/gamesys/SysCmds.cpp','neo/d3xp/Player.cpp','neo/d3xp/SmokeParticles.cpp']
    files['source/RBDoom-r15.patch'] = subprocess.check_output(['git','diff','--binary','--',*paths],cwd=source)
    report = {'revision':'r15', 'upstream':candidate.UPSTREAM,
              'toolCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
              'pose':'r12 unchanged', 'runtimeTest':'Not run in cloud; owner playtest required',
              'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
    files['reach-combat-build.json'] = json.dumps(report,indent=2).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as handle, zipfile.ZipFile(handle,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()): archive.writestr(name,data)
    print(json.dumps({'package':str(output),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    for name in ['engine','capture','source','repair']: parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    build(args.output,args.engine,args.capture,args.source,args.repair)


