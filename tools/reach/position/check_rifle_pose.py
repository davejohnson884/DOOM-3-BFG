"""Validate a scaled rifle-only offset instead of global gun placement."""
import math
import re
from build_preset import script, ROOT, REPO, PATTERN
from build_pose import script as previous_script
from test_pose import axes, rotate

body = (ROOT / 'reach_ar_pose.script').read_text()
assert 'setJointPos(reach_root_joint, JOINTMOD_LOCAL, reach_pose_shift)' in body
assert 'setJointAngle(reach_root_joint, JOINTMOD_WORLD, reach_pose_angles)' in body
assert not re.search(r'\b(?:setcvar|waitFrame|waitUntil)\s*\(', body)
assert '(reach_pose_gun_target - reach_pose_host_gun) * (1 / reach_pose_scale)' in body
assert 'if (reach_pose_scale != 0)' in body
assert re.sub(PATTERN, '', script().decode(), flags=re.S) == re.sub(
    PATTERN, '', previous_script().decode(), flags=re.S)
# The weapon entity is reused. Changing models must clear its old joint
# modifiers so the rifle's translation cannot leak into the next weapon.
animator = (REPO / 'neo/d3xp/anim/Anim_Blend.cpp').read_text()
set_model = re.search(r'idAnimator::SetModel\([^)]*\)\s*\{(.*?)\n\}', animator, re.S)[1]
free_data = re.search(r'void idAnimator::FreeData\(\)\s*\{(.*?)\n\}', animator, re.S)[1]
assert 'FreeData();' in set_model
assert 'jointMods.DeleteContents( true );' in free_data

# DoomScript supports float division and vector*float, not vector/float.
compiler = (REPO / 'neo/d3xp/script/Script_Compiler.cpp').read_text()
assert re.search(r'\{\s*"/".*?&def_float,\s*&def_float,\s*&def_float', compiler)
assert re.search(r'\{\s*"\*".*?&def_vector,\s*&def_float,\s*&def_vector', compiler)
assert not re.search(r'\{\s*"/".*?&def_vector', compiler)

cfg = (ROOT / 'reach_pose.cfg').read_text()
for axis, value in zip('XYZ', (-4, 4, 1)):
    assert f'set reach_arGun{axis} {value}' in cfg
    assert f'reset g_gun{axis}' in cfg
assert not re.search(r'\bseta?\s+g_gun[XYZ]\b', cfg)
# Confirm the restoration defaults rather than inventing stock positions.
cvars = (REPO / 'neo/d3xp/gamesys/SysCvar.cpp').read_text()
for axis, default in zip('XYZ', ('3', '0', '0')):
    assert re.search(r'"g_gun' + axis + r'"\s*,\s*"' + default + '"', cvars)

pivot = [15.84341446, -4.47929218, .28925242]
offset = [4, -4.2, -2.8]
target = [-4, 4, 1]
_, matrix = axes((0, 0, -3))
pivot_shift = [a - b for a, b in zip(pivot, rotate(matrix, pivot))]
checks = 0
for scale in (.5, .7, 1, 1.5):
    for host in ([3, 0, 0], [-4, 4, 1], [5, -2, 3]):
        shift = [pivot_shift[i] + (target[i] - host[i]) / scale for i in range(3)]
        for point in (pivot, [37.3, -4.48, -2.61], [6, 5, -9]):
            rotated = rotate(matrix, point)
            actual = [host[i] + scale * (rotated[i] + offset[i] + shift[i]) for i in range(3)]
            expected = [target[i] + scale * (rotated[i] + offset[i] + pivot_shift[i]) for i in range(3)]
            assert all(math.isclose(a, b, abs_tol=1e-10) for a, b in zip(actual, expected))
            checks += 1
        if list(host) == target:
            assert all(math.isclose(a, b, abs_tol=1e-10) for a, b in zip(shift, pivot_shift))
print(f'PASS: {checks} neutral-camera rifle anchor checks across scales/global offsets; '
      'no double translation; other weapon logic unchanged; script operator types verified.')
