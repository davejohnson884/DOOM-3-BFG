import hashlib
import io
import json
import math
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_reach import package, ROOT, digits, counter_material
from build_switch_diagnostic import build as build_switch_diagnostic, PAYLOAD
from build_switch_fix import build as build_switch_fix
from build_presentation_fix import build as build_presentation_fix
from presentation import entries as presentation_entries


class PackageChecks(unittest.TestCase):
    def test_view_pose_uses_additive_model_space_rotation(self):
        script = (ROOT/'reach_machinegun.script').read_text()
        body = re.search(r'void weapon_machinegun::ReachApplyViewPose\(\)\s*\{(.*?)\n\}', script, re.S)[1]
        call = re.search(r"setJointAngle\(reach_root_joint,\s*(\w+),\s*'([^']+)'\)", body)
        self.assertIsNotNone(call)
        self.assertEqual(call[1], 'JOINTMOD_WORLD', 'Override loses the donor root orientation; LOCAL rotates around its rolled axes')
        self.assertIn('getJointHandle("origin")', body)
        self.assertIn('if (reach_root_joint >= 0)', body)
        for state in ('init', 'Raise'):
            state_body = re.search(r'void weapon_machinegun::'+state+r'\(\)\s*\{(.*?)\n\}', script, re.S)[1]
            self.assertIn('ReachApplyViewPose();', state_body)
        self.assertNotRegex(script, r'\b(?:setJointPos|setcvar)\s*\(')

        # The actual engine WORLD branch post-multiplies row-axis matrices.
        # In conventional column coordinates this composes correction * source.
        repo = ROOT.parents[2]
        native = (repo/'neo/d3xp/anim/Anim_Blend.cpp').read_text()
        root = native[native.index('// check if we need to modify the origin'):]
        self.assertRegex(root, r'case JOINTMOD_WORLD:\s*joints\[0\].SetRotation\( joints\[0\].ToMat3\(\) \* jointMod->mat \);')
        pitch, yaw, roll = map(math.radians, map(float, call[2].split()))
        cp, sp, cy, sy, cr, sr = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw), math.cos(roll), math.sin(roll)
        correction = [[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                      [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
                      [-sp, cp*sr, cp*cr]]
        source_root = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        def mm(a, b): return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        def mv(a, v): return [sum(a[i][k]*v[k] for k in range(3)) for i in range(3)]
        combined = mm(correction, source_root)
        for child_point in ([20, 4, 3], [4, -8, 2], [0, 1, 0]):
            expected = mv(correction, mv(source_root, child_point))
            actual = mv(combined, child_point)
            for a, b in zip(actual, expected): self.assertAlmostEqual(a, b)
            self.assertAlmostEqual(sum(a*a for a in actual), sum(a*a for a in child_point))
        # These common mistakes are observably different with a nonidentity root.
        point = [20, 4, 3]
        expected = mv(combined, point)
        self.assertGreater(sum(abs(a-b) for a, b in zip(expected, mv(correction, point))), 1)
        self.assertGreater(sum(abs(a-b) for a, b in zip(expected, mv(mm(source_root, correction), point))), .01)

    def test_controller_spawn_classes_are_registered_and_concrete(self):
        # A valid name can still be an abstract class that fatally rejects Spawn.
        repo = Path(__file__).resolve().parents[3]
        registry = {}
        for source in (repo/'neo/d3xp').rglob('*.cpp'):
            text = re.sub(r'//[^\n]*|/\*.*?\*/', '', source.read_text(errors='replace'), flags=re.S)
            for kind, name in re.findall(r'\b(CLASS_DECLARATION|ABSTRACT_DECLARATION)\s*\(\s*\w+\s*,\s*(\w+)\s*\)', text):
                registry[name] = kind == 'CLASS_DECLARATION'
        self.assertIs(registry['idEntity'], False)
        spawn_classes = re.findall(r'"spawnclass"\s+"([^"]+)"', (ROOT/'reach_controls.def').read_text())
        self.assertTrue(spawn_classes)
        for name in spawn_classes:
            self.assertIn(name, registry, 'Unregistered native spawn class: '+name)
            self.assertTrue(registry[name], 'Cannot instantiate abstract native spawn class: '+name)

    def test_switch_fix_replaces_existing_overlay_without_assets_or_executables(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'fix.zip'
            build_switch_fix(output)
            with zipfile.ZipFile(output) as outer:
                self.assertIsNone(outer.testzip())
                self.assertEqual(set(outer.namelist()), {'reach/zzzz_reach_switch.pk4', 'REACH-SWITCH-FIX.txt', 'PROJECT-GPL.txt'})
                with zipfile.ZipFile(io.BytesIO(outer.read('reach/zzzz_reach_switch.pk4'))) as inner:
                    self.assertIsNone(inner.testzip())
                    self.assertEqual(set(inner.namelist()), set(PAYLOAD) | set(presentation_entries()))
                    for target, source in PAYLOAD.items():
                        self.assertEqual(inner.read(target), (ROOT/source).read_bytes())
            previous = output.read_bytes()
            with self.assertRaises(FileExistsError): build_switch_fix(output)
            self.assertEqual(output.read_bytes(), previous)

    def assets(self, root):
        assets = root/'converted'; assets.mkdir()
        (assets/'validation-report.json').write_text(json.dumps({'clips': 25, 'framesChecked': 844}))
        for category in ('models/md5/weapons/reach_ar', 'textures', 'materials', 'sound', 'def', 'script', 'stock-script', 'renderprogs'):
            (assets/category).mkdir(parents=True, exist_ok=True)
        (assets/'def/weapon_machinegun.def').write_text('entityDef weapon_machinegun {\n "clipSize" "32"\n}\n')
        (assets/'materials/reach_ar.mtr').write_text('reach/ones { { blend add map donor_zero.tga } }\nreach/tens { { blend add map donor_zero.tga } }\n')
        (assets/'models/md5/weapons/reach_ar/view.md5mesh').write_text('unchanged mesh fixture')
        (assets/'script/weapon_machinegun.script').write_text('scriptEvent float getReachPose();')
        (assets/'renderprogs/forbidden.glsl').write_text('old cache must not ship')
        (assets/'private-donor.json').write_text('not part of runtime pack')
        return assets

    def test_package_and_payload_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); assets = self.assets(root); output = root/'mod.zip'
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.rglob('*') if p.is_file()}
            report = package(assets, output)
            with zipfile.ZipFile(output) as outer:
                self.assertEqual(outer.testzip(), None)
                self.assertEqual(set(outer.namelist()), {'reach/zzz_reach_ar.pk4', 'reach/reach-package.json', 'Play-Reach.cmd', 'REACH-README.txt'})
                with zipfile.ZipFile(io.BytesIO(outer.read('reach/zzz_reach_ar.pk4'))) as inner:
                    self.assertIsNone(inner.testzip())
                    for name, digest in report['files'].items():
                        self.assertEqual(hashlib.sha256(inner.read(name)).hexdigest(), digest)
                    self.assertFalse(any('renderprogs' in p or 'private-donor' in p for p in inner.namelist()))
                    self.assertNotIn(b'getReachPose', inner.read('script/weapon_machinegun.script'))
                    self.assertEqual(inner.read('models/md5/weapons/reach_ar/view.md5mesh'), b'unchanged mesh fixture')
                    self.assertIn(b'"def_melee" "damage_reach_ar_melee"', inner.read('def/weapon_machinegun.def'))
                    smoke = re.search(r'"smoke_muzzle"\s+"([^"]+)"', inner.read('def/weapon_machinegun.def').decode())[1]
                    particle_name = re.search(r'particle\s+(\S+)', inner.read('particles/reach_ar_flash.prt').decode())[1]
                    self.assertEqual(smoke, particle_name, 'Native particle lookup uses the exact declaration name, including .prt')
                    config = inner.read('autoexec.cfg')
                    self.assertNotRegex(config.decode(), r'(r_fullscreen|r_window|com_smp|jobs_numThreads|r_useParallel|fs_basepath|fs_savepath|fs_resourceLoadPriority)')
            self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
            previous = output.read_bytes()
            with self.assertRaises(FileExistsError): package(assets, output)
            self.assertEqual(output.read_bytes(), previous)

    def test_rejects_missing_or_unvalidated_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); assets = self.assets(root)
            (assets/'validation-report.json').write_text('{"clips": 24, "framesChecked": 844}')
            with self.assertRaises(ValueError): package(assets, root/'mod.zip')
            self.assertFalse((root/'mod.zip').exists())
            (assets/'validation-report.json').write_text('{"clips": 25, "framesChecked": 844}')
            (assets/'materials/reach_ar.mtr').write_text('reach/ones { }')
            with self.assertRaises(ValueError): package(assets, root/'mod.zip')
            self.assertFalse((root/'mod.zip').exists())

    def test_digits_and_source_uv_mapping(self):
        image = digits()
        self.assertEqual(len(image), 18+640*64*4)
        # Every digit has lit pixels and a distinct bitmap.
        tiles = []
        for digit in range(10):
            pixels = b''.join(image[18+(y*640+digit*64)*4:18+(y*640+(digit+1)*64)*4] for y in range(64))
            self.assertTrue(any(pixels))
            tiles.append(pixels)
        self.assertEqual(len(set(tiles)), 10)
        # Evaluate the actual authored order, using the engine's post-multiply rule.
        # The earlier scale-then-translate version incorrectly scaled the offset.
        materials = [presentation_entries()['materials/reach_presentation.mtr'].decode(),
                     counter_material('reach/ones { }\nreach/tens { }')]
        for text in materials:
            for name, parm in [('ones', 10), ('tens', 9)]:
                body = re.search(r'reach/(?:rb_)?'+name+r'\s*\{(?:[^{}]|\{[^{}]*\})*\}', text, re.S)[0]
                transforms = re.findall(r'\b(translate|scale)\s+([^,\n]+),\s*([^\n]+)', body)
                self.assertEqual(len(transforms), 2)
                for ammo in range(33):
                    digit = ammo % 10 if name == 'ones' else ammo // 10
                    slope, offset = 1., 0.
                    for action, u, _ in transforms:
                        value = digit/10 - .05 if u.strip() == 'parm'+str(parm)+' - 0.05' else float(u)
                        if action == 'translate': offset += slope*value
                        else: slope *= value
                    self.assertAlmostEqual(.25*slope+offset, digit/10)
                    self.assertAlmostEqual(.75*slope+offset, (digit+1)/10)

    def test_presentation_overlay_dependencies_and_private_content_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'presentation.zip'
            build_presentation_fix(output)
            with zipfile.ZipFile(output) as outer:
                self.assertIsNone(outer.testzip())
                self.assertEqual(set(outer.namelist()), {'reach/zzzz_reach_switch.pk4', 'REACH-PRESENTATION-FIX.txt', 'PROJECT-GPL.txt', 'Play-Reach.cmd', 'Play-Reach-diagnostic.cmd'})
                with zipfile.ZipFile(io.BytesIO(outer.read('reach/zzzz_reach_switch.pk4'))) as inner:
                    self.assertIsNone(inner.testzip())
                    self.assertEqual(set(inner.namelist()), set(PAYLOAD) | set(presentation_entries()))
                    for name, value in presentation_entries().items(): self.assertEqual(inner.read(name), value)
                    skin = inner.read('skins/reach_presentation.skin').decode()
                    material = inner.read('materials/reach_presentation.mtr').decode()
                    self.assertNotIn('glass_shattered', material)
                    targets = re.findall(r'\breach/(?:display|ones|tens)\s+(reach/\w+)', skin)
                    self.assertEqual(len(targets), 3)
                    for target in targets: self.assertRegex(material, re.escape(target)+r'\s*\{')
                    script = inner.read('script/weapon_machinegun.script').decode()
                    model_name = re.search(r'setModel\("([^"]+)"\)', script)[1]
                    model = inner.read('def/reach_presentation.def').decode()
                    self.assertRegex(model, r'model\s+'+model_name+r'\s*\{')
                    self.assertRegex(model, r'inherit\s+viewmodel_reach_ar\b')
                    self.assertNotRegex(model, r'\b(mesh|anim|entityDef)\b')
                    self.assertNotRegex(script, r'\bsetcvar\s*\(')
                    self.assertIn('else { setSkin("reach_ar_clean_display"); }', script)
                    config = inner.read('reach_controls.cfg').decode()
                    self.assertIn('bind V "trigger reach_melee_input"', config)
                    self.assertNotRegex(config, r'(g_fov|g_gun|r_fullscreen|jobs_numThreads|com_smp)')
            previous = output.read_bytes()
            with self.assertRaises(FileExistsError): build_presentation_fix(output)
            self.assertEqual(output.read_bytes(), previous)

    def test_script_variables_and_existing_event_interface(self):
        # Public stock engine events reject variable redeclarations (move was a real bug).
        repo = Path(__file__).resolve().parents[3]
        events = set()
        for source in (repo/'neo/d3xp').rglob('*.cpp'):
            events.update(re.findall(r'\bidEventDef\s+\w+\s*\(\s*"([^"\n]+)"', source.read_text(errors='replace')))
        events.update(re.findall(r'\bidEventDef\s+\w+\s*\(\s*"([^"\n]+)"', (repo/'neo/d3xp/script/Script_Thread.cpp').read_text()))
        self.assertIn('move', events)
        for name in ('reach_machinegun.script', 'reach_controls.script'):
            text = (ROOT/name).read_text()
            stripped = re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)
            variables = set(re.findall(r'\b(?:float|vector|entity|boolean|string)\s+(\w+)\s*(?=[;,\)])', stripped))
            self.assertEqual(variables & events, set())
            self.assertNotIn('scriptEvent', stripped)
            object_events = set(re.findall(r'\b(?:sys|reach_player|reach_weapon|reach_round)\.(\w+)\(', stripped))
            self.assertEqual(object_events-events, set())

    def test_native_round_preparation_preserves_launch_momentum(self):
        # Native collision impulse depends on mass as well as imported speed.
        # Check the actual script formula for stock and faster donor speeds.
        text = (ROOT/'reach_machinegun.script').read_text()
        host_speed = float(re.search(r'reach_round_mass\s*=\s*reach_round.getFloatKey\("mass"\)\s*\*\s*([0-9.]+)\s*/\s*reach_round_speed', text)[1])
        for mass in (0.1, 1., 2.):
            for speed in (host_speed, 360000., 720000.):
                adjusted = mass * host_speed / speed
                self.assertGreater(adjusted, 0)
                self.assertAlmostEqual(adjusted*speed, mass*host_speed)
        self.assertIn('reach_round.setKey("mass", "" + reach_round_mass);', text)
        self.assertIn('reach_round.setKey("push", "0");', text)
        self.assertNotRegex(text, r'reach_round.setKey\("(?:velocity|def_damage)"')

    def test_diagnostic_update_is_script_only_and_preserves_previous_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'update.zip'
            capture = Path(temp)/'ReachDebugLog.exe'
            capture.write_bytes(b'MZ capture packaging fixture')
            build_switch_diagnostic(output, capture)
            before = output.read_bytes()
            with zipfile.ZipFile(output) as outer:
                self.assertIsNone(outer.testzip())
                self.assertEqual(set(outer.namelist()), {'reach/zzzz_reach_switch.pk4', 'Play-Reach-diagnostic.cmd', 'REACH-SWITCH-DIAGNOSTIC.txt', 'PROJECT-GPL.txt', 'ReachDebugLog.exe', 'ReachDebugLog.cs'})
                self.assertEqual(outer.read('ReachDebugLog.exe'), capture.read_bytes())
                with zipfile.ZipFile(io.BytesIO(outer.read('reach/zzzz_reach_switch.pk4'))) as inner:
                    self.assertIsNone(inner.testzip())
                    self.assertEqual(set(inner.namelist()), set(PAYLOAD) | set(presentation_entries()))
                    for target, source in PAYLOAD.items():
                        self.assertEqual(inner.read(target), (ROOT/source).read_bytes())
                # Released RBDoom scans sorted PK4 names in reverse order.
                self.assertGreater('zzzz_reach_switch.pk4', 'zzz_reach_ar.pk4')
                launcher = outer.read('Play-Reach-diagnostic.cmd').decode()
                self.assertNotRegex(launcher, r'(?i)(powershell|r_fullscreen|r_window|com_smp|jobs_numThreads|r_useParallel|fs_basepath|fs_savepath|fs_resourceLoadPriority)')
            with self.assertRaises(FileExistsError): build_switch_diagnostic(output, capture)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__': unittest.main()
