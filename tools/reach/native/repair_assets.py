"""Repair installed private Reach assets; no MCC re-extraction or recoloring.

Use fresh render-asset names to bypass cached binary models/images. Preserve
the installed TACPAD geometry, all animation values, original art and pose.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

MODEL = 'models/md5/weapons/reach_ar/'
OUTPUT = 'zzzzzzzzzzz_reach_repair_r15.pk4'
OPAQUE = ('spartan_fp_armor','spartan_fp_glove','spartan_rubber_suit','spartan_armor',
          'spartan_forearm_tricorder','assault_rifle_composite','assault_rifle_metal',
          'assault_rifle_metal_shiny','assault_rifle_rubber')


def declaration(text,name):
    match=re.search(r'\bmodel\s+'+re.escape(name)+r'\s*\{',text)
    if match is None: raise ValueError('Missing original model declaration: '+name)
    level=1;quoted=False;escaped=False
    for i in range(match.end(),len(text)):
        ch=text[i]
        if ch=='"' and not escaped:quoted=not quoted
        if not quoted:
            if ch=='{':level+=1
            elif ch=='}':level-=1
            if level==0:return text[match.start():i+1]
        escaped=ch=='\\' and not escaped
    raise ValueError('Unterminated original model declaration')


def repair(game):
    game=Path(game).resolve();folder=game/'reach'
    paths=[folder/n for n in ['zzz_reach_ar.pk4','zzzzzzzz_reach_appearance.pk4','zzzzzzzzzz_reach_effects.pk4']]
    for path in paths:
        if not path.is_file():raise FileNotFoundError('Required installed Reach pack is missing: '+str(path))
    entries={}
    with zipfile.ZipFile(paths[0]) as base,zipfile.ZipFile(paths[1]) as appearance,zipfile.ZipFile(paths[2]) as effects:
        for archive in [base,appearance,effects]:
            if archive.testzip() is not None:raise ValueError('Installed PK4 failed CRC verification')
        mesh=appearance.read(MODEL+'view.md5mesh').decode()
        if 'reach/spartan_forearm_tricorder' not in mesh:raise ValueError('Installed appearance pack does not contain the TACPAD mesh')
        materials=appearance.read('materials/reach_ar.mtr').decode()
        appearance_materials=[]
        for name in OPAQUE:
            pattern=r'reach/'+re.escape(name)+r'\s*\{(?:[^{}]|\{[^{}]*\})*\}'
            match=re.search(pattern,materials)
            if match is None:raise ValueError('Missing installed material: '+name)
            new_name='reach/repair15/'+name
            mesh=mesh.replace('shader "reach/'+name+'"','shader "'+new_name+'"')
            block=match[0].replace('reach/'+name,new_name,1)
            block=block.replace('textures/reach/appearance/','textures/reach/repair15/')
            appearance_materials.append(block)
        for item in appearance.infolist():
            if item.filename.startswith('textures/reach/appearance/'):
                entries[item.filename.replace('textures/reach/appearance/','textures/reach/repair15/',1)]=appearance.read(item)
            if item.filename.startswith(MODEL) and item.filename.endswith('.md5anim'):
                entries[item.filename.replace(MODEL,MODEL+'r15/',1)]=appearance.read(item)
        entries[MODEL+'view_appearance_r15.md5mesh']=mesh.encode()
        original_def=base.read('def/weapon_machinegun.def').decode()
        model=declaration(original_def,'viewmodel_reach_ar')
        model=model.replace('model viewmodel_reach_ar','model viewmodel_reach_ar_appearance_r15',1)
        model=model.replace(MODEL,MODEL+'r15/')
        model=model.replace(MODEL+'r15/view.md5mesh',MODEL+'view_appearance_r15.md5mesh')
        entries['def/reach_presentation.def']=(model+'''
model viewmodel_reach_ar_present {
    inherit viewmodel_reach_ar_appearance_r15
    offset ( 4 -4.2 -2.8 )
}
''').encode()
        for item in effects.infolist():
            if item.filename.startswith('textures/reach/effects14/'):
                entries[item.filename.replace('textures/reach/effects14/','textures/reach/effects15/',1)]=effects.read(item)
            elif item.filename.startswith('textures/reach/appearance/'):
                entries[item.filename.replace('textures/reach/appearance/','textures/reach/repair15/',1)]=effects.read(item)
        fx=effects.read('materials/reach_effects14.mtr').decode()
        fx=fx.replace('reach/effects14/','reach/effects15/').replace('reach/appearance/','reach/repair15/')
        fx=fx.replace('reach/frag_grenade_metal','reach/repair15/frag_grenade_metal')
        entries['materials/reach_repair15.mtr']=('\n'.join(appearance_materials)+'\n'+fx).encode()
        for name in ['reach_ar_flash','reach_frag_explosion']:
            old_path='particles/'+name+'.prt'
            text=effects.read(old_path).decode().replace('initialAngle','angle')
            text=text.replace('reach/effects14/','reach/effects15/')
            entries[old_path]=text.encode() # stop legacy weapon precache from parsing invalid syntax
            fresh=text.replace('particle '+name+'.prt','particle '+name+'_r15.prt',1)
            entries['particles/'+name+'_r15.prt']=fresh.encode()
        obj=effects.read('models/reach/frag_grenade.obj').decode()
        entries['models/reach/frag_grenade_r15.obj']=obj.replace('usemtl reach/frag_grenade_metal','usemtl reach/repair15/frag_grenade_metal').encode()
        frag=effects.read('def/reach_frag.def').decode()
        frag=frag.replace('models/reach/frag_grenade.obj','models/reach/frag_grenade_r15.obj')
        frag=frag.replace('reach_frag_explosion.prt','reach_frag_explosion_r15.prt')
        entries['def/reach_frag.def']=frag.encode()
        report={'revision':'r15','sourcePacks':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                'changes':['valid particle angle syntax','new model/image/material/animation names to bypass stale caches'],
                'poseChanged':False,'geometryChanged':False,'animationValuesChanged':False,'pixelsChanged':False,
                'armorPalette':'Previous approximate steel tint retained; exact Noble Six preset not yet recovered',
                'runtimeTest':'Owner game test required',
                'files':{n:hashlib.sha256(b).hexdigest() for n,b in entries.items()}}
        entries['reach-repair15-report.json']=json.dumps(report,indent=2).encode()
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
        for name,payload in sorted(entries.items()):z.writestr(name,payload)
    output=folder/OUTPUT
    # Finish and verify a staged archive before replacing our own repair output.
    with tempfile.NamedTemporaryFile(dir=folder,prefix='reach-r15-',suffix='.tmp',delete=False) as handle:
        staged=Path(handle.name);handle.write(data.getvalue())
    try:
        with zipfile.ZipFile(staged) as z:
            if z.testzip() is not None:raise ValueError('Repair PK4 failed CRC verification')
        staged.replace(output)
    finally:
        staged.unlink(missing_ok=True)
    (game/'reach-repair-r15-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Repair complete: '+str(output))
    print('Start Play-Reach-projection.cmd. No manual exec is needed.')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    repair(parser.parse_args().game)
