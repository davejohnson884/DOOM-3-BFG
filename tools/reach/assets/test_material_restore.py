"""Check the installed-pack rollback without donor game data."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image
from build_polish import MATERIAL_FILE, PACK as POLISH_PACK, PARTICLES, REPAIR, SURFACES, material_block
from restore_materials import DIAGNOSTIC, PACK, PAINT, TACPAD, restore


def tga(size, color):
    data = io.BytesIO(); Image.new('RGBA', size, color).save(data, format='TGA'); return data.getvalue()


def write_pack(path, entries):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items(): archive.writestr(name, payload)


def make_fixture(game):
    game = Path(game).resolve(); folder = game/'reach'; folder.mkdir(parents=True, exist_ok=True)
    original = {}; polish = {}; old_materials = ''; new_materials = ''
    for name in SURFACES:
        old = 'textures/reach/repair15/'+name
        fresh = 'textures/reach/polish16_pbr_2x/'+name
        body = 'reach/repair15/'+name+'\n{\n bumpmap '+old+'_normal.tga\n diffusemap '+old+'_diffuse.tga\n specularmap '+old+'_specular.tga\n'
        for role, color in [('normal', (128, 128, 255, 255)), ('diffuse', (180, 170, 160, 255)), ('specular', (40, 50, 60, 255))]:
            original[old+'_'+role+'.tga'] = tga((4, 2), color)
        if name == TACPAD:
            original[old+'_illum.tga'] = tga((4, 2), (0, 128, 254, 255))
            body += ' {\n blend add\n map '+old+'_illum.tga\n }\n'
        old_materials += body+'}\n'
        new_materials += 'reach/repair15/'+name+'\n{\n bumpmap '+fresh+'_normal.tga\n diffusemap '+fresh+'_diffuse.tga\n rmaomap '+fresh+'_rmao.tga\n}\n'
        if name in PAINT: polish[fresh+'_diffuse.tga'] = tga((8, 4), (70, 70, 70, 255))
    for name in ['ar_round', 'ar_long', 'frag_fireball', 'smoke', 'blast']:
        path = 'textures/reach/effects16/'+name+'.tga'
        old_materials += 'reach/effects15/'+name+'\n{\n {\n blend add\n map textures/reach/effects15/'+name+'.tga\n }\n}\n'
        original['textures/reach/effects15/'+name+'.tga'] = tga((4, 4), (20, 20, 20, 255))
        new_materials += 'reach/effects15/'+name+'\n{\n {\n blend add\n map '+path+'\n }\n}\n'
        polish[path] = tga((4, 4), (60, 40, 20, 0))
    for name in PARTICLES: polish['particles/'+name+'.prt'] = ('particle '+name+'.prt { }').encode()
    original[MATERIAL_FILE] = old_materials.encode(); polish[MATERIAL_FILE] = new_materials.encode()
    write_pack(folder/REPAIR, original); write_pack(folder/POLISH_PACK, polish)
    (folder/'unrelated.pk4').write_bytes(b'user mod')
    return original, polish


def verify_output(game, original, polish):
    folder = Path(game)/'reach'
    assert not (folder/POLISH_PACK).exists()
    assert (folder/'unrelated.pk4').read_bytes() == b'user mod'
    with zipfile.ZipFile(folder/PACK) as archive:
        assert archive.testzip() is None
        materials = archive.read(MATERIAL_FILE).decode()
        original_materials = original[MATERIAL_FILE].decode()
        for name in SURFACES:
            body = material_block(materials, 'reach/repair15/'+name)[0]
            assert 'rmaomap' not in body
            if name not in PAINT: assert body == material_block(original_materials, 'reach/repair15/'+name)[0]
        for role in ['diffuse', 'normal', 'specular', 'illum']:
            path = 'textures/reach/repair15/'+TACPAD+'_'+role+'.tga'
            assert archive.read(path) == original[path]
        for name in PAINT:
            with Image.open(io.BytesIO(archive.read('textures/reach/restore17/'+name+'_diffuse.tga'))) as image:
                assert image.size == (4, 2)
                assert image.getpixel((0, 0)) == (70, 70, 70, 255)
        for name, payload in polish.items():
            if name.startswith(('textures/reach/effects16/', 'particles/')):
                assert archive.read(name) == payload
        assert not any(n.endswith(('.md5mesh', '.md5anim', '.script', '.def', '.exe', '.dll')) for n in archive.namelist())
        cfg = archive.read(DIAGNOSTIC).decode()
        assert 'r_skipBump\n' in cfg and 'r_skipBump 0' not in cfg
        assert 'r_skipSpecular\n' in cfg and 'r_skipSpecular 0' not in cfg
        assert 'printMaterial reach/repair15/'+TACPAD in cfg
        report = json.loads(archive.read('reach-material-restore17-report.json'))
        for name, sha in report['files'].items(): assert hashlib.sha256(archive.read(name)).hexdigest() == sha


class RestoreTests(unittest.TestCase):
    def test_complete_tacpad_rollback_keeps_paint_and_effects(self):
        with tempfile.TemporaryDirectory(prefix='Reach restore test ') as temp:
            game = Path(temp).resolve(); original, polish = make_fixture(game)
            before = (game/'reach'/REPAIR).read_bytes()
            with redirect_stdout(io.StringIO()): restore(game, game/'custom save')
            verify_output(game, original, polish)
            self.assertEqual((game/'reach'/REPAIR).read_bytes(), before)
            # Re-running finds the retained disabled r16 source and is safe.
            with redirect_stdout(io.StringIO()): restore(game, game/'custom save')
            verify_output(game, original, polish)

    def test_already_disabled_r16_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp).resolve(); original, polish = make_fixture(game)
            p = game/'reach'/POLISH_PACK; p.rename(p.with_name(p.name+'.disabled-owner'))
            with redirect_stdout(io.StringIO()): restore(game, game/'custom save')
            verify_output(game, original, polish)

    def test_incomplete_source_does_not_disable_or_replace_installed_pack(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp).resolve(); original, polish = make_fixture(game)
            del original['textures/reach/repair15/'+TACPAD+'_illum.tga']
            write_pack(game/'reach'/REPAIR, original)
            before = (game/'reach'/POLISH_PACK).read_bytes()
            with self.assertRaises(KeyError): restore(game, game/'custom save')
            self.assertEqual((game/'reach'/POLISH_PACK).read_bytes(), before)
            self.assertFalse((game/'reach'/PACK).exists())


if __name__ == '__main__': unittest.main()
