"""Build a private playable weapon pack from owned Reach/BFG files."""
import base64
import json
import math
import re
import struct
import sys
from pathlib import Path


def raw(record):
    return base64.b64decode(record['raw'], validate=True)


def stats(bundle):
    w = json.loads((bundle/'weapon-raw.json').read_text())
    mag = raw(w['children']['Magazines']['elements'][0])
    barrel = raw(w['children']['Barrels']['elements'][0])
    rate = struct.unpack_from('<2f', barrel, 4)
    angles = struct.unpack_from('<2f', barrel, 0x74)
    bullet = json.loads(next((bundle/'combat-metadata').glob('*bullet.jpt*.json')).read_text())
    damage = struct.unpack_from('<3f', raw(bullet), 0x20)
    projectile = json.loads(next((bundle/'combat-metadata').glob('*bullet.proj.json')).read_text())
    melee = json.loads(next((bundle/'combat-metadata').glob('*strike_melee.jpt*.json')).read_text())
    result = {'roundsPerSecond': rate, 'clipSize': struct.unpack_from('<h', mag, 10)[0],
              'initialTotalAmmo': struct.unpack_from('<h', mag, 6)[0], 'maximumTotalAmmo': struct.unpack_from('<h', mag, 8)[0],
              'spreadDegrees': [math.degrees(a) for a in angles], 'spreadRecoverySeconds': struct.unpack_from('<f', barrel, 0x50)[0],
              'haloBulletDamage': damage, 'bfgBulletDamage': round(sum(damage[1:])/2),
              'haloMeleeDamage': struct.unpack_from('<f', raw(melee), 0x20)[0],
              'velocityBfgUnits': struct.unpack_from('<f', raw(projectile), 0x2d0)[0]*120}
    if rate[0] != rate[1] or rate[0] <= 0 or result['clipSize'] <= 0 or not 0 < result['spreadRecoverySeconds'] < 10:
        raise ValueError('Unsupported weapon tuning')
    return result


def resource_file(install, name):
    """Read one stock text declaration without extracting/modifying game installs."""
    for container in ['_common.resources', '_ordered.resources']:
        path = Path(install)/'base'/container
        with path.open('rb') as f:
            magic, table, size = struct.unpack('>3I', f.read(12))
            total = path.stat().st_size
            if magic != 3489660941 or table < 12 or size < 4 or size > 64*1024*1024 or table+size > total:
                raise ValueError('Unexpected BFG resource header')
            f.seek(table); count = struct.unpack('>I', f.read(4))[0]
            if count > 1000000: raise ValueError('Resource entry limit exceeded')
            for _ in range(count):
                length = struct.unpack('<i', f.read(4))[0]
                if length < 1 or length > 4096 or f.tell()+length+8 > table+size: raise ValueError('Bad resource name')
                filename = f.read(length).decode('utf-8').replace('\\', '/')
                offset, payload_length = struct.unpack('>2I', f.read(8))
                if filename == name:
                    if payload_length > 16*1024*1024 or offset < 12 or offset+payload_length > total:
                        raise ValueError('Invalid declaration payload')
                    f.seek(offset); payload = f.read(payload_length)
                    if len(payload) != payload_length: raise ValueError('Truncated declaration')
                    return payload.decode('utf-8-sig').replace('\r\n', '\n')
    raise FileNotFoundError('Stock declaration not found: '+name)


def replace_keys(text, declaration, changes):
    pattern = re.compile(r'(entityDef\s+'+re.escape(declaration)+r'\s*\{)(.*?)(\n\})', re.S)
    match = pattern.search(text)
    if match is None: raise ValueError('Missing declaration: '+declaration)
    body = match[2]
    for key, value in changes.items():
        expression = re.compile(r'"'+re.escape(key)+r'"\s+"[^"\n]*"')
        replacement = '"'+key+'" "'+str(value)+'"'
        if expression.search(body): body = expression.sub(lambda _: replacement, body)
        else: body += '\n    '+replacement
    return text[:match.start()]+match[1]+body+match[3]+text[match.end():]


def build(bundle, output, original_def):
    bundle = Path(bundle); output = Path(output)
    info = json.loads((output/'conversion-report.json').read_text())
    tuning = stats(bundle)
    anims = info['animations']
    def primary(clip):
        return next(e['frame'] for e in anims[clip]['events'] if e['type'] == 1)
    melee_windup = round(primary('melee_strike_1')/30*1000)
    grenade_windup = round(primary('throw_grenade')/30*1000)
    recover = next(e['frame'] for e in anims['sprint_exit']['events'] if e['type'] == 2)
    changes = {'model_view': 'viewmodel_reach_ar', 'weapon_scriptobject': 'weapon_machinegun', 'clipSize': tuning['clipSize'],
               'inv_name': 'Reach MA37', 'display_name': 'Reach MA37', 'def_projectile': 'projectile_reach_ar',
               'reach_has_pose_anims': 1, 'reach_melee_windup_ms': melee_windup,
               'reach_melee_recover_ms': round(anims['melee_strike_1']['frames']/30*1000)-melee_windup,
               'reach_grenade_windup_ms': grenade_windup,
               'reach_grenade_recover_ms': round(anims['throw_grenade']['frames']/30*1000)-grenade_windup,
               'reach_sprint_recover_ms': round(recover/30*1000), 'def_reach_melee': 'damage_reach_ar_melee',
               'reach_fire_interval': 1/tuning['roundsPerSecond'][0], 'reach_spread_min': tuning['spreadDegrees'][0],
               'reach_spread_max': tuning['spreadDegrees'][1], 'reach_spread_recovery': tuning['spreadRecoverySeconds'],
               'reach_reload_fill_time': primary('reload_empty')/30,
               'muzzle_kick_offset': '0 0 0', 'muzzle_kick_angles': '0 0 0', 'recoilAngles': '0 0 0',
               'smoke_joint': 'barrel'}
    definition = replace_keys(original_def, 'weapon_machinegun', changes)
    definition += '\nentityDef projectile_reach_ar {\n    "inherit" "projectile_bullet_machinegun"\n    "def_damage" "damage_reach_ar_bullet"\n    "velocity" "'+str(tuning['velocityBfgUnits'])+' 0 0"\n}\n'
    definition += '\nentityDef damage_reach_ar_bullet {\n    "inherit" "damage_bullet_machinegun"\n    "damage" "'+str(tuning['bfgBulletDamage'])+'"\n}\n'
    definition += '\nentityDef damage_reach_ar_melee {\n    "inherit" "damage_fists"\n    "damage" "'+str(round(tuning['haloMeleeDamage']))+'"\n}\n'
    # Sound events use actual exported sample groups (no Halo sound tags are needed in BFG).
    samples = info['sounds']; sound_lines = []
    groups = {'fire': '_ar_fire_', 'ready': '_ar_ready_', 'reload_empty': '_ar_reload_empty_',
              'reload_full': '_ar_reload_full_', 'melee': '_ar_melee_1_', 'throw_grenade': '_frag_throw_'}
    for label, token in groups.items():
        files = [s['file'] for s in samples if token in s['file'] and '_elite_' not in s['file']]
        if not files: raise ValueError('Missing required sound group: '+label)
        sound_lines.extend(['reach_ar_'+label, '{', '    minDistance 5', '    maxDistance 35', '    volume 0'])
        sound_lines += ['    '+f for f in files]
        sound_lines.append('}')
    (output/'sound/reach_ar.sndshd').write_text('\n'.join(sound_lines)+'\n')
    aliases = {'raise': 'ready', 'idle': 'idle', 'putaway': 'put_away', 'fire1': 'fire_1_var1', 'fire2': 'fire_1_var2',
               'fire3': 'fire_1_var3', 'reload_empty': 'reload_empty', 'reload_full': 'reload_full', 'melee': 'melee_strike_1',
               'throw_grenade': 'throw_grenade', 'sprint_enter': 'sprint_enter', 'sprint_loop': 'sprint_loop', 'sprint_exit': 'sprint_exit'}
    definition += '\nmodel viewmodel_reach_ar {\n    mesh models/md5/weapons/reach_ar/view.md5mesh\n'
    for label, source in aliases.items():
        sound = 'fire' if label.startswith('fire') else 'ready' if label == 'raise' else label if label in groups else None
        definition += '    anim '+label+' models/md5/weapons/reach_ar/'+source+'.md5anim'
        if sound: definition += ' { frame 1 sound_body reach_ar_'+sound+' }'
        definition += '\n'
    for label in anims:
        if label not in aliases: definition += '    anim source_'+label+' models/md5/weapons/reach_ar/'+label+'.md5anim\n'
    definition += '}\n'
    (output/'def').mkdir(); (output/'def/weapon_machinegun.def').write_text(definition)
    (output/'script').mkdir()
    template = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))/'reach_ar.script'
    (output/'script/weapon_machinegun.script').write_text(template.read_text())
    # Retail preview uses existing stock script events only. Full quick actions
    # remain in the native version above, whose getReachPose event is new.
    stock_script = template.read_text().replace('scriptEvent float getReachPose();', '')
    stock_script = stock_script.replace('getReachPose()', 'RetailReachPose()')
    stock_script = stock_script.replace('object weapon_machinegun : weapon_base {', '''object weapon_machinegun : weapon_base {
    float retail_sprinting;
    float retail_ready_time;
    float RetailReachPose();''')
    stock_script += '''
float weapon_machinegun::RetailReachPose() {
    entity owner;
    vector move;
    float requested;
    float now;
    owner = getOwner();
    move = owner.getMove();
    now = sys.getTime();
    requested = owner.getButtons() & 2;
    if (requested && sys.vecLength(move) > 0 && now >= retail_ready_time) {
        retail_sprinting = 1;
        return 1;
    }
    if (retail_sprinting) {
        retail_sprinting = 0;
        retail_ready_time = now + 0.3;
    }
    if (now < retail_ready_time) { return 4; }
    return 0;
}
'''
    (output/'stock-script').mkdir()
    (output/'stock-script/weapon_machinegun.script').write_text(stock_script)
    tuning['timingOverrides'] = {k: v for k, v in changes.items() if k.endswith('_ms')}
    tuning['limitations'] = ['Bloom uses a linear approximation; original penalty function payloads were not collected.',
                             'BFG bullet damage rounds the original fractional range to an integer.',
                             'Grenade projectile/world weapon remain BFG assets; on-rifle digits currently contain only zero.',
                             'Requires this project source build with getReachPose; runtime stability and appearance need an owner playtest.']
    (output/'weapon-tuning.json').write_text(json.dumps(tuning, indent=2)+'\n')
    return tuning
