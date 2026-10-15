"""Exercise repair output and check particle keywords against the pinned parser.

Fixtures contain no game assets. Private donor validation is recorded separately.
"""
import contextlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile

from repair_assets import MODEL, OPAQUE, OUTPUT, repair

SOURCE = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else None


def particle_keywords(source):
    parser = (source/'neo/framework/DeclParticle.cpp').read_text()
    stage = parser.split('idParticleStage* idDeclParticle::ParseParticleStage')[1].split('bool idDeclParticle::Parse(')[0]
    return set(re.findall(r'!token.Icmp\(\s*"([^"]+)"', stage))


def check_particle(text, accepted):
    depth = 0
    for line in text.splitlines():
        line = line.strip()
        if depth == 2 and line and not line.startswith(('//', '}')):
            key = line.split()[0]
            if key not in accepted:
                raise ValueError('Unsupported particle stage keyword: '+key)
        depth += line.count('{') - line.count('}')
    if depth != 0:
        raise ValueError('Unbalanced particle declaration')


def write_pack(folder, name, entries):
    path = folder/name
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for key, value in entries.items():
            archive.writestr(key, value)
    return path


class RepairTests(unittest.TestCase):
    def test_installed_assets_preserved_and_old_caches_bypassed(self):
        with tempfile.TemporaryDirectory(prefix='Reach repair test ') as root:
            game = Path(root); folder = game/'reach'; folder.mkdir()
            base = {'def/weapon_machinegun.def': '''
entityDef weapon_machinegun { "model_view" "viewmodel_reach_ar" }
model viewmodel_reach_ar {
 mesh models/md5/weapons/reach_ar/view.md5mesh
 anim idle models/md5/weapons/reach_ar/idle.md5anim
 anim fire1 models/md5/weapons/reach_ar/fire.md5anim {
  frame 1 sound snd_fire
 }
}
model unrelated { mesh other.md5mesh }
'''}
            mesh = '\n'.join('mesh { shader "reach/'+n+'" numverts 0 numtris 0 numweights 0 }' for n in OPAQUE)
            # Include non-opaque ammo-counter surfaces: they must remain shared.
            mesh += '\nmesh { shader "reach/ar_counter_tens" }\n'
            materials = '\n'.join('reach/'+n+'\n{\n bumpmap textures/reach/appearance/'+n+'_normal.tga\n'
                                  ' diffusemap textures/reach/appearance/'+n+'_diffuse.tga\n'
                                  ' specularmap textures/reach/appearance/'+n+'_specular.tga\n}' for n in OPAQUE)
            appearance = {MODEL+'view.md5mesh': mesh, 'materials/reach_ar.mtr': materials}
            for name in OPAQUE:
                for role in ['normal', 'diffuse', 'specular']:
                    appearance['textures/reach/appearance/'+name+'_'+role+'.tga'] = b'pixel bytes '+name.encode()+role.encode()
            for name in ['idle', 'fire']:
                appearance[MODEL+name+'.md5anim'] = b'unchanged animation '+name.encode()
            particle = '''particle NAME.prt {
    {
        count 1
        material reach/effects14/ar_round
        time 0.115
        cycles 1
        orientation view
        initialAngle 0.001
        animationFrames 2
        color 1 1 1 1
    }
}
'''
            effects = {
                'particles/reach_ar_flash.prt': particle.replace('NAME', 'reach_ar_flash'),
                'particles/reach_frag_explosion.prt': particle.replace('NAME', 'reach_frag_explosion'),
                'materials/reach_effects14.mtr': '''reach/effects14/ar_round {
 { blend add map textures/reach/effects14/ar_round.tga }
}
reach/frag_grenade_metal { diffusemap textures/reach/appearance/frag_grenade_metal_diffuse.tga }
''',
                'textures/reach/effects14/ar_round.tga': b'original flash pixels',
                'textures/reach/appearance/frag_grenade_metal_diffuse.tga': b'original frag pixels',
                'models/reach/frag_grenade.obj': 'v 1 2 3\nvn 0 1 0\nvt .2 .8\nusemtl reach/frag_grenade_metal\nf 1/1/1 1/1/1 1/1/1\n',
                'def/reach_frag.def': '''entityDef projectile_reach_frag {
 "model" "models/reach/frag_grenade.obj"
 "model_detonate" "reach_frag_explosion.prt"
 "reach_floor_fuse" "1"
 "fuse" "45"
}
''',
            }
            paths = [write_pack(folder, n, entries) for n, entries in zip(
                ['zzz_reach_ar.pk4', 'zzzzzzzz_reach_appearance.pk4', 'zzzzzzzzzz_reach_effects.pk4'],
                [base, appearance, effects])]
            originals = {p: p.read_bytes() for p in paths}
            with contextlib.redirect_stdout(io.StringIO()):
                report = repair(game)
                repair(game)  # Re-running replaces only the completed repair output.
            self.assertEqual({p: p.read_bytes() for p in paths}, originals)
            self.assertFalse(report['poseChanged'])
            self.assertFalse(report['pixelsChanged'])
            self.assertIn('approximate', report['armorPalette'])
            self.assertEqual({p.name for p in game.iterdir()}, {'reach', 'reach-repair-r15-report.json'})
            with zipfile.ZipFile(folder/OUTPUT) as archive:
                self.assertIsNone(archive.testzip())
                output_mesh = archive.read(MODEL+'view_appearance_r15.md5mesh').decode()
                # Remove shader identifiers and independently compare the geometry text.
                strip = lambda text: re.sub(r'shader "[^"]+"', 'shader ""', text)
                self.assertEqual(strip(output_mesh), strip(mesh))
                self.assertIn('shader "reach/ar_counter_tens"', output_mesh)
                self.assertNotIn('shader "reach/spartan_forearm_tricorder"', output_mesh)
                for key, data in appearance.items():
                    if key.endswith('.md5anim'):
                        self.assertEqual(archive.read(key.replace(MODEL, MODEL+'r15/', 1)), data)
                    if key.endswith('.tga'):
                        self.assertEqual(archive.read(key.replace('/appearance/', '/repair15/')), data)
                for key, data in effects.items():
                    if key.endswith('.tga'):
                        self.assertEqual(archive.read(key.replace('/effects14/', '/effects15/').replace('/appearance/', '/repair15/')), data)
                declaration = archive.read('def/reach_presentation.def').decode()
                self.assertIn('offset ( 4 -4.2 -2.8 )', declaration)
                self.assertIn('frame 1 sound snd_fire', declaration)
                self.assertNotIn('unrelated', declaration)
                self.assertIn(MODEL+'r15/fire.md5anim', declaration)
                self.assertIn(MODEL+'view_appearance_r15.md5mesh', declaration)
                self.assertIn('"reach_floor_fuse" "1"', archive.read('def/reach_frag.def').decode())
                accepted = particle_keywords(SOURCE)
                self.assertIn('angle', accepted)
                self.assertNotIn('initialAngle', accepted)
                with self.assertRaisesRegex(ValueError, 'initialAngle'):
                    check_particle(particle, accepted)
                for name in archive.namelist():
                    if name.endswith('.prt'):
                        check_particle(archive.read(name).decode(), accepted)

    def test_missing_donor_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                repair(root)
            self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == '__main__':
    if SOURCE is None:
        raise SystemExit('Usage: test_repair.py <pinned RBDoom source>')
    unittest.main()
