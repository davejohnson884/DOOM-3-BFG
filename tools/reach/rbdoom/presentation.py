"""Authored rifle presentation declarations; reference existing private textures."""

MODEL_DEF = '''model viewmodel_reach_ar_present {
    inherit viewmodel_reach_ar
    offset ( 8 -1 -1 )
}
'''

SKIN = '''skin reach_ar_clean_display {
    reach/display reach/rb_display
    reach/ones reach/rb_ones
    reach/tens reach/rb_tens
}
'''


def material():
    text = '''reach/rb_display
{
    twoSided
    translucent
    noShadows
    {
        blend add
        map textures/reach/objects_weapons_rifle_assault_rifle_bitmaps_display_plate_self_illum.tga
    }
}
'''
    for name, parm in [('ones', 10), ('tens', 9)]:
        # idMaterial post-multiplies matrices: T*S gives scale*u + offset.
        text += '''reach/rb_NAME
{
    twoSided
    translucent
    noShadows
    {
        blend add
        map textures/reach/rb_digits.tga
        translate parmPARM - 0.05, 0
        scale 0.2, 1
    }
}
'''.replace('NAME', name).replace('PARM', str(parm))
    return text


def entries():
    return {'def/reach_presentation.def': MODEL_DEF.encode(),
            'skins/reach_presentation.skin': SKIN.encode(),
            'materials/reach_presentation.mtr': material().encode()}
