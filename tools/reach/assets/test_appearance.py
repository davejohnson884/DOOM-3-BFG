"""Small format/math checks; donor geometry is validated privately on all frames."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from build_appearance import combine_normals, tiled, extract


class AppearanceTests(unittest.TestCase):
    def test_flat_detail_preserves_base_normal(self):
        base = np.array([[[.3,.4,np.sqrt(.75)]]])
        np.testing.assert_allclose(combine_normals(base,np.array([[[0.,0.,1.]]])),base,atol=1e-12)

    def test_periodic_uv_sampling(self):
        image = Image.fromarray(np.array([[[0,0,0,255],[255,255,255,255]]],dtype=np.uint8))
        sampled = tiled(image,(8,1),(2,1))
        np.testing.assert_allclose(sampled[:,:4],sampled[:,4:])
        np.testing.assert_allclose(sampled[...,3],1)

    def test_donor_zip_paths_rejected(self):
        for name in ['../escape','/escape','C:/escape','safe/../../escape']:
            with tempfile.TemporaryDirectory() as root:
                stream = io.BytesIO()
                with zipfile.ZipFile(stream,'w') as z:z.writestr(name,b'never write this')
                with zipfile.ZipFile(stream) as z:
                    with self.assertRaises(ValueError):extract(z,Path(root))


if __name__=='__main__':unittest.main()
