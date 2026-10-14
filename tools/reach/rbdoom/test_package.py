import hashlib
import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_reach import package, ROOT, digits, counter_material
from build_switch_diagnostic import build as build_switch_diagnostic, PAYLOAD


class PackageChecks(unittest.TestCase):
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
        for ammo in range(33):
            ones = ammo % 10; tens = (ammo-ones)//10
            for digit in (tens, ones):
                self.assertAlmostEqual(.25*.2+digit/10-.05, digit/10)
                self.assertAlmostEqual(.75*.2+digit/10-.05, (digit+1)/10)

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
            object_events = set(re.findall(r'\b(?:sys|reach_player|reach_weapon)\.(\w+)\(', stripped))
            self.assertEqual(object_events-events, set())

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
                    self.assertEqual(set(inner.namelist()), set(PAYLOAD))
                    for target, source in PAYLOAD.items():
                        self.assertEqual(inner.read(target), (ROOT/source).read_bytes())
                # Released RBDoom scans sorted PK4 names in reverse order.
                self.assertGreater('zzzz_reach_switch.pk4', 'zzz_reach_ar.pk4')
                launcher = outer.read('Play-Reach-diagnostic.cmd').decode()
                self.assertNotRegex(launcher, r'(?i)(powershell|r_fullscreen|r_window|com_smp|jobs_numThreads|r_useParallel|fs_basepath|fs_savepath|fs_resourceLoadPriority)')
            with self.assertRaises(FileExistsError): build_switch_diagnostic(output, capture)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__': unittest.main()
