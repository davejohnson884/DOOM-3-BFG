import io
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from convert_reach import read_codec, flags, md5q, read_dds, sounds
from check_md5 import engine_matrix
from build_weapon import resource_file, replace_keys


class ConversionChecks(unittest.TestCase):
    def test_known_quaternion_in_bfg_convention(self):
        # A real +90-degree Z rotation must send +X to +Y in BFG.
        q = np.array([0., 0., math.sqrt(.5), math.sqrt(.5)])
        m = engine_matrix(md5q(q), [0, 0, 0])
        np.testing.assert_allclose(m[:3, 0], [0, 1, 0], atol=1e-12)

    def test_two_frame_quantized_clip(self):
        data = struct.pack('<4B2f5I', 3, 1, 0, 0, 0, .3, 48, 48, 16, 24, 8)
        data += struct.pack('<8h', 0, 0, 0, 32767, 0, 0, 23170, 23170)
        values, end, info = read_codec(data, 0, 2, 3)
        self.assertEqual(end, 48)
        np.testing.assert_allclose(values[0][0, 0], [0, 0, 0, 1])
        np.testing.assert_allclose(values[0][0, 1], [0, 0, math.sqrt(.5), math.sqrt(.5)])
        with self.assertRaises(ValueError): read_codec(data[:-1], 0, 2, 3)
        with self.assertRaises(ValueError): read_codec(bytes([10])+data[1:], 0, 2, 3)

    def test_node_mask_bit_order(self):
        data = struct.pack('<6I', 1, 1<<19, 2, 0, 0, 0)
        mask = flags(data, 0, 24, 52)
        self.assertEqual(np.where(mask[0])[0].tolist(), [0, 51])
        self.assertEqual(np.where(mask[1])[0].tolist(), [1])

    def test_bgra_dds_read(self):
        with tempfile.TemporaryDirectory() as root:
            data = bytearray(148); data[:4] = b'DDS '
            struct.pack_into('<I', data, 4, 124); struct.pack_into('<II', data, 12, 1, 2)
            data[84:88] = b'DX10'; struct.pack_into('<I', data, 128, 87)
            path = Path(root)/'sample.dds'; path.write_bytes(data+bytes([3, 2, 1, 255, 30, 20, 10, 128]))
            self.assertEqual(np.array(read_dds(path)).reshape(-1, 4).tolist(), [[1, 2, 3, 255], [10, 20, 30, 128]])

    def test_four_channel_audio_duration(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); donor = root/'donor'; output = root/'output'
            (donor/'sounds').mkdir(parents=True); output.mkdir()
            pcm = np.full((480, 4), .25, dtype='<f4').tobytes()
            data = b'RIFF'+struct.pack('<I', 36+len(pcm))+b'WAVEfmt '+struct.pack('<IHHIIHH', 16, 3, 4, 48000, 768000, 16, 32)+b'data'+struct.pack('<I', len(pcm))+pcm
            (donor/'sounds/sample.wav').write_bytes(data)
            result = sounds(donor, output)
            import wave
            with wave.open(str(output/result[0]['file']), 'rb') as wav:
                self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()), (1, 2, 44100, 441))
                samples = np.frombuffer(wav.readframes(441), '<i2')
                self.assertTrue(np.all(np.abs(samples-8192) <= 1))

    def test_owned_resource_lookup_and_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); (root/'base').mkdir()
            filename = b'def/weapon_machinegun.def'; payload = b'entityDef weapon_machinegun {\n "clipSize" "60"\n}\n'
            table = struct.pack('>I', 1)+struct.pack('<i', len(filename))+filename+struct.pack('>II', 12, len(payload))
            path = root/'base/_common.resources'
            path.write_bytes(struct.pack('>III', 3489660941, 12+len(payload), len(table))+payload+table)
            original = resource_file(root, filename.decode())
            patched = replace_keys(original, 'weapon_machinegun', {'clipSize': 32, 'reach_has_pose_anims': 1})
            self.assertIn('"clipSize" "32"', patched)
            self.assertEqual(resource_file(root, filename.decode()), original)
            path.write_bytes(b'NOT A CACHE!')
            with self.assertRaises(ValueError): resource_file(root, filename.decode())


if __name__ == '__main__': unittest.main()
