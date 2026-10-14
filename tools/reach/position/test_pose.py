"""Check the new pivot math against engine axes and the original root pose."""
import ast
import io
import json
import math
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from build_pose import build, script, PATTERN, ROOT, REPO, PK4_PATH, DECL_PATH, SCRIPT_PATH
from build_position import DECLARATION
from build_candidate import script as projection_script


def expression(text, values):
    # Evaluate only arithmetic from idAngles::ToVectors/ToMat3, not arbitrary
    # source code. This makes the engine's actual axes the math reference.
    def visit(node):
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
        raise ValueError('Unexpected engine axis expression: ' + text)
    return visit(ast.parse(text.strip(), mode='eval').body)


def axes(angles):
    source = (REPO / 'neo/idlib/math/Angles.cpp').read_text()
    vectors = re.search(r'void idAngles::ToVectors\([^)]*\)\s*const\s*\{(.*?)\n\}', source, re.S)[1]
    matrix = re.search(r'idMat3 idAngles::ToMat3\(\) const\s*\{(.*?)\n\}', source, re.S)[1]
    values = {}
    for name, degrees in zip(('p', 'y', 'r'), angles):
        values['s' + name] = math.sin(math.radians(degrees))
        values['c' + name] = math.cos(math.radians(degrees))
    v = [[expression(t, values) for t in terms.split(',')]
         for terms in re.findall(r'->Set\( (.*?) \);', vectors)]
    m = [[expression(t, values) for t in terms.split(',')]
         for terms in re.findall(r'mat\[ \d \].Set\( (.*?) \);', matrix)]
    if len(v) != 3 or len(m) != 3:
        raise ValueError('Expected the three released engine axes')
    return v, m


def rotate(columns, point):
    return [sum(columns[j][i] * point[j] for j in range(3)) for i in range(3)]


class PoseChecks(unittest.TestCase):
    def test_counter_pivot_and_nonidentity_root(self):
        body = (ROOT / 'reach_pose.script').read_text()
        self.assertIn('setJointAngle(reach_root_joint, JOINTMOD_WORLD, reach_pose_angles)', body)
        self.assertIn('setJointPos(reach_root_joint, JOINTMOD_LOCAL, reach_pose_shift)', body)
        self.assertRegex(body, r'-\s*sys\.angToRight\(reach_pose_angles\) \* reach_pose_pivot_y')
        pivot = list(map(float, re.search(r"reach_pose_pivot = '([^']+)'", body)[1].split()))
        animation = (REPO / 'neo/d3xp/anim/Anim_Blend.cpp').read_text()
        origin = animation[animation.index('// check if we need to modify the origin'):]
        self.assertRegex(origin, r'case JOINTMOD_WORLD:\s*joints\[0\].SetRotation\( joints\[0\].ToMat3\(\) \* jointMod->mat \);')
        self.assertRegex(origin, r'case JOINTMOD_LOCAL:\s*joints\[0\].SetTranslation\( joints\[0\].ToVec3\(\) \+ jointMod->pos \);')
        # Donor root is a 90-degree roll, not identity. An axis override or
        # composition on its rolled local axes changes the original animation.
        donor = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]  # columns
        for angles in ((0, 0, 0), (0, 0, -3), (-2, 2, -3), (4, -7, 5)):
            (forward, right, up), matrix = axes(angles)
            columns = [forward, [-v for v in right], up]
            self.assertEqual(columns, matrix)
            shift = [a - b for a, b in zip(pivot, rotate(columns, pivot))]
            fixed = [a + b for a, b in zip(rotate(matrix, pivot), shift)]
            for a, b in zip(fixed, pivot): self.assertAlmostEqual(a, b, places=10)
            # A rigid correction must retain distances for hands and markers.
            points = [[20, 4, 3], [4, -8, 2], [37.3, -4.48, -2.61]]
            posed = [rotate(donor, p) for p in points]
            corrected = [[a + b for a, b in zip(rotate(matrix, p), shift)] for p in posed]
            before = sum((posed[0][i] - posed[1][i]) ** 2 for i in range(3))
            after = sum((corrected[0][i] - corrected[1][i]) ** 2 for i in range(3))
            self.assertAlmostEqual(before, after, places=9)
            if angles == (0, 0, 0):
                self.assertEqual(corrected, posed)

    def test_calls_use_existing_script_api(self):
        source = (REPO / 'neo/d3xp/script/Script_Thread.cpp').read_text()
        for name, args, result in [('angToForward', 'v', 'v'), ('angToRight', 'v', 'v'),
                                   ('angToUp', 'v', 'v'), ('strToFloat', 's', 'f'),
                                   ('getcvar', 's', 's')]:
            self.assertRegex(source, r'idEventDef\s+\w+\(\s*"' + name + r'",\s*"' + args + r'",\s*\'' + result + r'\'\s*\)')
        entity = (REPO / 'neo/d3xp/Entity.cpp').read_text()
        for name in ('setJointAngle', 'setJointPos'):
            self.assertRegex(entity, r'idEventDef\s+\w+\(\s*"' + name + r'",\s*"ddv"\s*\)')
        body = (ROOT / 'reach_pose.script').read_text()
        self.assertNotRegex(body, r'\b(?:setcvar|waitFrame|waitUntil)\s*\(')
        self.assertIn("reach_pose_angles = '0 0 -3';", body)
        for name in ('reach_arPitch', 'reach_arYaw', 'reach_arRoll'):
            self.assertIn('sys.getcvar("' + name + '") != ""', body)

    def test_state_bodies_fields_and_projection_tag_are_retained(self):
        original, changed = projection_script().decode(), script().decode()
        self.assertEqual(re.sub(PATTERN, '', original, flags=re.S), re.sub(PATTERN, '', changed, flags=re.S))
        self.assertIn('setShaderParm(6, 1)', changed)
        for state in ('init', 'Raise'):
            body = re.search(r'void weapon_machinegun::' + state + r'\(\)\s*\{(.*?)\n\}', changed, re.S)[1]
            self.assertIn('ReachApplyViewPose();', body)

    def test_package_replaces_r9_without_replacing_projection_or_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'pose.zip'
            build(output)
            with zipfile.ZipFile(output) as outer:
                self.assertIsNone(outer.testzip())
                self.assertEqual(set(outer.namelist()), {PK4_PATH, 'REACH-POSE-README.txt', 'reach-pose-build.json'})
                report = json.loads(outer.read('reach-pose-build.json'))
                self.assertFalse(report['projectionChanged'])
                self.assertEqual(report['changedFromR9'], [SCRIPT_PATH])
                with zipfile.ZipFile(io.BytesIO(outer.read(PK4_PATH))) as inner:
                    self.assertIsNone(inner.testzip())
                    self.assertEqual(set(inner.namelist()), {DECL_PATH, SCRIPT_PATH})
                    self.assertEqual(inner.read(DECL_PATH), DECLARATION)
            previous = output.read_bytes()
            with self.assertRaises(FileExistsError): build(output)
            self.assertEqual(output.read_bytes(), previous)


if __name__ == '__main__':
    unittest.main(verbosity=2)
