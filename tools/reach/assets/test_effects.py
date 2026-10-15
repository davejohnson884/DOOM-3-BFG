import base64
import unittest
import struct
import numpy as np
from build_effects import sample_wrap, sprite_rectangles, frag_definition


class EffectChecks(unittest.TestCase):
    def test_source_uv_rectangles_repeat(self):
        source=np.array([[[0.,0.,0.,0.],[1.,1.,1.,1.]]])
        u=np.array([[.25,.75]]);v=np.array([[.5,.5]])
        np.testing.assert_allclose(sample_wrap(source,u,v),sample_wrap(source,u+7,v+8))
        np.testing.assert_allclose(sample_wrap(source,u,v)[0,:,0],[0,1])

    def test_runtime_sprite_table_preserves_source_order(self):
        def row(v):return {'raw':base64.b64encode(struct.pack('<4f',*v)).decode()}
        table={'children':{'Unknown':{'elements':[row((2,0,0,0)),row((.5,0,.5,1)),row((0,0,.5,1))]}}}
        self.assertEqual(sprite_rectangles(table),[(.5,0,.5,1),(0,0,.5,1)])
        table['children']['Unknown']['elements'].pop()
        with self.assertRaises(ValueError):sprite_rectangles(table)

    def test_frag_definition_does_not_explode_on_contact(self):
        tuning={'airGravityScale':.9,'armingTime':1.4,'timerRange':[.6,.65],'damage':160,'radiusBfg':270}
        text=frag_definition(tuning)
        for key in ['detonate_on_world','detonate_on_actor','detonate_on_trigger','detonate_on_fuse']:
            self.assertIn('"'+key+'" "0"',text)
        self.assertIn('"reach_floor_fuse" "1"',text)
        self.assertIn('"reach_arming_time" "1.4"',text)
        self.assertIn('models/reach/frag_grenade.obj',text)


if __name__=='__main__':unittest.main()
