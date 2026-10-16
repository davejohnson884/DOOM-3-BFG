"""Regression checks for alpha coverage, armor masks and targeted cache updates."""
import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from PIL import Image
from build_effects import bake_palette, particle_alpha_source
from build_polish import (PARTICLES, armor_multiplier, bake_material, move_particle_caches,
                          padded_atlas, read_palette, to_linear, to_srgb)

SOURCE = None
if '--source' in sys.argv:
    index = sys.argv.index('--source')
    SOURCE = Path(sys.argv[index+1]); del sys.argv[index:index+2]


def particle(option):
    def row(values): return {'raw': base64.b64encode(struct.pack('<4f', *values)).decode()}
    return {'children': {
        'Template Identifier': {'elements': [{'raw': base64.b64encode(struct.pack('<h', option)).decode()}]},
        'Unknown': {'elements': [row((1, 0, 0, 0)), row((1/3, 1/3, 1/3, 1/3))]},
        'Postprocess': {'elements': [{'children': {'Textures': {'elements': [
            {}, {}, {'fields': [{'kind': 'tagref', 'tagClass': 'bitm', 'tag': 'coverage'}]}]}}}]}}}


class PolishTests(unittest.TestCase):
    def test_fireball_uses_billboard_mask_instead_of_tiled_noise_alpha(self):
        noise = np.ones((3, 3, 4)); palette = np.ones((1, 2, 4))
        coverage = np.zeros((3, 3, 4)); coverage[1, 1, 3] = 1
        data = {'noise': noise, 'palette': palette, 'coverage': coverage}
        with patch('build_effects.record', return_value=particle(3)), patch('build_effects.bitmap', side_effect=lambda b, tag: data[tag]):
            pixels, count = bake_palette('.', 'particle', 'noise', 'palette', (3, 3))
        self.assertEqual(count, 1)
        np.testing.assert_array_equal(pixels[0], 0)
        np.testing.assert_array_equal(pixels[-1], 0)
        np.testing.assert_array_equal(pixels[:, 0], 0)
        np.testing.assert_array_equal(pixels[:, -1], 0)
        np.testing.assert_allclose(pixels[1, 1], 1)

    def test_sprite_alpha_uses_sprite_uvs_and_premultiplies_once(self):
        noise = np.ones((3, 3, 4)); palette = np.ones((1, 2, 4))
        coverage = np.zeros((3, 3, 4)); coverage[1, 1, 3] = .5
        data = {'noise': noise, 'palette': palette, 'coverage': coverage}
        with patch('build_effects.record', return_value=particle(5)), patch('build_effects.bitmap', side_effect=lambda b, tag: data[tag]):
            pixels, count = bake_palette('.', 'particle', 'noise', 'palette', (3, 3))
        np.testing.assert_allclose(pixels[1, 1], .5)
        self.assertGreater(pixels[0, 0, 3], 0)  # sprite samples its center rectangle
        with self.assertRaisesRegex(ValueError, 'albedo option'):
            particle_alpha_source(particle(0))

    def test_steel_masks_are_independent_and_do_not_tint_blue_channel(self):
        masks = np.array([[[0., 0., 1.], [1., 0., 0.], [0., 1., 0.], [1., 1., 0.]]])
        steel = np.array([.12, .12, .12])
        expected = np.array([[[1., 1., 1.], [.12, .12, .12], [.12, .12, .12], [.0144, .0144, .0144]]])
        np.testing.assert_allclose(armor_multiplier(masks, steel), expected)

    def test_color_transfer_roundtrip_and_neutral(self):
        values = np.linspace(0, 1, 256)
        np.testing.assert_allclose(to_srgb(to_linear(values)), values, atol=1e-7)
        self.assertAlmostEqual(float(to_srgb(to_linear(np.array(.5)))), .5)

    def test_atlas_filtering_isolated_and_final_crossfade_is_black(self):
        source = np.ones((4, 8, 4))
        atlas, count = padded_atlas(source, 2, gutter=2)
        self.assertEqual(count, 4)
        tiles = np.split(atlas, count, axis=1)
        for tile in tiles:
            np.testing.assert_array_equal(tile[:2], 0)
            np.testing.assert_array_equal(tile[-2:], 0)
            np.testing.assert_array_equal(tile[:, :2], 0)
            np.testing.assert_array_equal(tile[:, -2:], 0)
        np.testing.assert_array_equal(tiles[-1], 0)
        np.testing.assert_array_equal(tiles[-2], 0)
        np.testing.assert_array_equal(tiles[0][2:-2, 2:-2], 1)

    def test_material_emission_is_not_armor_tinted_and_normals_remain_unit(self):
        maps = [SimpleNamespace(texture_usage=n, texture_index=i, tiling=(1., 1.), channel_mask=8 if n=='specular' else 7)
                for i, n in enumerate(['diffuse', 'normal', 'specular', 'color_change', 'self_illum'])]
        images = {'diffuse': Image.new('RGBA', (4, 4), (180, 180, 180, 128)),
                  'normal': Image.new('RGBA', (4, 4), (128, 128, 255, 255)),
                  'specular': Image.new('RGBA', (4, 4), (180, 180, 180, 128)),
                  'color_change': Image.new('RGBA', (4, 4), (255, 0, 0, 255)),
                  'self_illum': Image.new('RGBA', (4, 4), (0, 128, 255, 255))}
        scene = SimpleNamespace(texture_pool=[SimpleNamespace(name=m.texture_usage) for m in maps])
        mat = SimpleNamespace(name='spartan_forearm_tricorder', texture_mappings=maps,
                              tints=[SimpleNamespace(tint_usage='self_illum', tint_color=(162, 206, 254, 255))])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in images: (root/(name+'.dds')).touch()
            for lighting in ['classic', 'pbr']:
                entries = {}
                with patch('build_polish.read_dds', side_effect=lambda p: images[p.stem]):
                    body, report = bake_material(scene, mat, root, entries, np.array([.126902]*3), 2, lighting)
                loaded = {Path(n).stem.rsplit('_', 1)[-1]: np.asarray(Image.open(io.BytesIO(b))) for n, b in entries.items()}
                self.assertEqual(loaded['diffuse'].shape, (8, 8, 4))
                np.testing.assert_array_equal(loaded['illum'][0, 0, :3], [0, 103, 254])
                n = loaded['normal'][..., :3].astype(float)/255*2-1
                np.testing.assert_allclose(np.linalg.norm(n, axis=-1), 1, atol=.01)
                self.assertIn('rmaomap' if lighting=='pbr' else 'specularmap', body)
                if lighting=='pbr':
                    np.testing.assert_array_equal(loaded['rmao'][..., 1], 0)
                    np.testing.assert_array_equal(loaded['rmao'][..., 2], 255)
                    np.testing.assert_array_equal(loaded['rmao'][..., 3], 128)

    def test_only_named_particle_caches_moved_and_backed_up(self):
        with tempfile.TemporaryDirectory(prefix='Reach cache test ') as temp:
            root = Path(temp); saved = root/'Saved Games'
            originals = {}
            for directory in [root/'reach/generated/particles', saved/'reach/generated/particles']:
                directory.mkdir(parents=True)
                for name in PARTICLES:
                    p = directory/(name+'.bprt'); p.write_bytes(name.encode()); originals[p] = p.read_bytes()
                (directory/'stock_smoke.bprt').write_bytes(b'stock cache')
            (saved/'reach/D3BFGConfig.cfg').write_bytes(b'user preferences')
            moved = move_particle_caches(root, saved)
            self.assertEqual(len(moved), 4)
            for item in moved:
                p = Path(item['original']); self.assertFalse(p.exists())
                self.assertEqual(Path(item['backup']).read_bytes(), originals[p])
            self.assertEqual((saved/'reach/D3BFGConfig.cfg').read_bytes(), b'user preferences')
            self.assertEqual((saved/'reach/generated/particles/stock_smoke.bprt').read_bytes(), b'stock cache')
            self.assertEqual(move_particle_caches(root, saved), [])

    def test_palette_integrity_is_checked_before_use(self):
        import hashlib
        raw = b''.join(struct.pack('<fff', *([v]*3)) for v in [.1, .3, .7]+[.2]*27)
        doc = {'schemaVersion': 1, 'schema': 'ReachMCC/matg.xml', 'tableOffset': 0x498,
               'ElementSize': 12, 'Count': 30, 'rawSha256': hashlib.sha256(raw).hexdigest(),
               'BuildString': 'fixture', 'profileColors': [{'index': i, 'rgb': list(v)}
                   for i, v in enumerate(struct.iter_unpack('<fff', raw))]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'palette.zip'
            def save():
                with zipfile.ZipFile(path, 'w') as z:
                    z.writestr('profile-colors.bin', raw); z.writestr('profile-colors.json', json.dumps(doc))
            save(); steel, report = read_palette(path)
            np.testing.assert_allclose(steel, [.1]*3)
            doc['rawSha256'] = '0'*64; save()
            with self.assertRaisesRegex(ValueError, 'layout'): read_palette(path)

    @unittest.skipIf(SOURCE is None, 'Pinned host source not supplied')
    def test_generated_stage_keywords_and_rmao_match_pinned_host(self):
        from build_effects import stage
        parser = (SOURCE/'neo/framework/DeclParticle.cpp').read_text()
        parser = parser.split('idParticleStage* idDeclParticle::ParseParticleStage')[1].split('bool idDeclParticle::Parse(')[0]
        accepted = set(re.findall(r'!token.Icmp\(\s*"([^"]+)"', parser))
        for line in stage('fixture', .1, '1', frames=4).splitlines():
            key = line.strip().split()[0]
            if key not in ['{', '}']: self.assertIn(key, accepted)
        material = (SOURCE/'neo/renderer/Material.cpp').read_text()
        self.assertIn('!token.Icmp( "rmaomap" )', material)


if __name__ == '__main__': unittest.main()
