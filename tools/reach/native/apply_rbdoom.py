"""Apply the opt-in presentation extension to the exact released RBDoom source."""
import argparse
from pathlib import Path
import subprocess

UPSTREAM = 'ba39ba67df049dcf16c7b31f6613f72959be2c21'
ROOT = Path(__file__).resolve().parent
MARKER = 'Reach opt-in weapon projection'


def replace(text, old, new, name):
    if text.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one source anchor; refusing a fuzzy patch')
    return text.replace(old, new, 1)


def apply(root):
    root = Path(root).resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if head != UPSTREAM:
        raise ValueError('This patch requires the owner-tested RBDoom release commit ' + UPSTREAM)
    paths = ['neo/renderer/RenderCommon.h', 'neo/renderer/tr_frontend_addmodels.cpp',
             'neo/renderer/RenderBackend.cpp', 'neo/d3xp/Weapon.cpp', 'neo/d3xp/Weapon.h', 'neo/d3xp/Projectile.cpp',
             'neo/d3xp/gamesys/SysCmds.cpp', 'neo/d3xp/Player.cpp']
    original = {path: (root/path).read_text(encoding='utf-8-sig') for path in paths}
    if any(MARKER in text for text in original.values()):
        raise ValueError('Source already patched; start with a clean pinned source snapshot')
    for path in paths:
        committed = subprocess.check_output(['git', 'show', 'HEAD:'+path], cwd=root).decode('utf-8-sig')
        if original[path] != committed.replace('\r\n', '\n'):
            raise ValueError('Preserve existing edits; source differs from the pinned release: ' + path)
    changed = dict(original)

    path = paths[0]
    changed[path] = replace(changed[path],
        '\tbool\t\t\t\t\tweaponDepthHack;\n',
        '\tbool\t\t\t\t\tweaponDepthHack;\n'
        '\tbool\t\t\t\t\treachWeaponProjection; // Reach opt-in weapon projection; frame-local only\n', path)

    path = paths[1]
    changed[path] = replace(changed[path], '#include "Model_local.h"\n', '''#include "Model_local.h"
#include "ReachWeaponProjection.h"

// Reach opt-in weapon projection. No archive flag: the ordinary port defaults
// are retained on a subsequent launch without the candidate's enable command.
idCVar r_reachWeaponFov( "r_reachWeaponFov", "0", CVAR_RENDERER | CVAR_FLOAT | CVAR_NOCHEAT,
	"Reach first-person horizontal FOV at 4:3; 0 retains the released projection", 0.0f, 175.0f );

static bool R_ReachProjectionEligible( const renderEntity_t& ent, const viewDef_t& view )
{
	return r_reachWeaponFov.GetFloat() > 0.0f && ent.hModel != NULL &&
		ReachProjection::Eligible( ent.hModel->Name(), ent.shaderParms[6] == 1.0f,
			ent.weaponDepthHack, ent.allowSurfaceInViewID, view.renderView.viewID,
			view.isSubview, view.isMirror );
}
''', path)
    changed[path] = replace(changed[path],
        '\tconst bool modelIsVisible = !vEntity->scissorRect.IsEmpty();\n',
        '''	const bool modelIsVisible = !vEntity->scissorRect.IsEmpty();
	const bool reachProjectionEligible = R_ReachProjectionEligible( *renderEntity, *viewDef );
	if( modelIsVisible && reachProjectionEligible )
	{
		// World-projected portal rectangles cannot crop the magnified FP model.
		vEntity->scissorRect = viewDef->scissor;
	}
''', path)
    changed[path] = replace(changed[path],
        '''	idRenderMatrix::Multiply( viewDef->projectionRenderMatrix, viewMat, vEntity->mvp );
	idRenderMatrix::Multiply( viewDef->unjitteredProjectionRenderMatrix, viewMat, vEntity->unjitteredMVP );
''', '''	vEntity->reachWeaponProjection = false;
	if( reachProjectionEligible )
	{
		idRenderMatrix reachProjection = viewDef->projectionRenderMatrix;
		idRenderMatrix reachUnjitteredProjection = viewDef->unjitteredProjectionRenderMatrix;
		const float aspect = float( viewDef->viewport.x2 - viewDef->viewport.x1 + 1 ) /
			float( viewDef->viewport.y2 - viewDef->viewport.y1 + 1 );
		const float fov = r_reachWeaponFov.GetFloat();
		vEntity->reachWeaponProjection = ReachProjection::Apply( reachProjection[0], fov, aspect ) &&
			ReachProjection::Apply( reachUnjitteredProjection[0], fov, aspect );
		if( vEntity->reachWeaponProjection )
		{
			idRenderMatrix::Multiply( reachProjection, viewMat, vEntity->mvp );
			idRenderMatrix::Multiply( reachUnjitteredProjection, viewMat, vEntity->unjitteredMVP );
			// No world-projection motion vectors for this first-person entity.
			vEntity->skipMotionBlur = true;
		}
	}
	if( !vEntity->reachWeaponProjection )
	{
		// Retain the original released path for every ordinary entity.
		idRenderMatrix::Multiply( viewDef->projectionRenderMatrix, viewMat, vEntity->mvp );
		idRenderMatrix::Multiply( viewDef->unjitteredProjectionRenderMatrix, viewMat, vEntity->unjitteredMVP );
	}
''', path)

    path = paths[2]
    anchor = '''			if( surf->space != currentSpace )
			{
				currentSpace = surf->space;

				// turn off the light depth bounds test'''
    changed[path] = replace(changed[path], anchor, '''			if( surf->space != currentSpace )
			{
				currentSpace = surf->space;

				// Reach opt-in weapon projection: light rectangles use the world
				// camera. Broaden only this FP draw and restore for normal spaces.
				const idScreenRect& projectionScissor = surf->space->reachWeaponProjection ?
					viewDef->scissor : vLight->scissorRect;
				if( r_useScissor.GetBool() && !currentScissor.Equals( projectionScissor ) )
				{
					GL_Scissor( viewDef->viewport.x1 + projectionScissor.x1,
						viewDef->viewport.y2 - projectionScissor.y2,
						projectionScissor.x2 + 1 - projectionScissor.x1,
						projectionScissor.y2 + 1 - projectionScissor.y1 );
					currentScissor = projectionScissor;
				}

				// turn off the light depth bounds test''', path)

    path = paths[3]
    changed[path] = replace(changed[path], '#include "Game_local.h"',
                            '#include "Game_local.h"\n#include "ReachQuickActions.h"', path)
    changed[path] = replace(changed[path],
        '\t\tconst idKeyValue* lkv = weaponDef->dict.MatchPrefix( "weapon_light", NULL );\n',
        '''		// Reach opt-in weapon projection: the candidate script tags its
		// model during construction. Use an owned emitter so the flash follows
		// the same FP projection instead of the shared world smoke geometry.
		if( idStr::Cmp( spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0 &&
			idStr::Cmp( spawnArgs.GetString( "weapon_scriptobject" ), "weapon_machinegun" ) == 0 )
		{
			const idDeclEntityDef* emitterDef = gameLocal.FindEntityDef( "func_emitter", false );
			if( emitterDef != NULL && barrelJointView != INVALID_JOINT )
			{
				idDict args = emitterDef->dict;
				args.Set( "model", "reach_ar_flash_r15.prt" );
				args.SetBool( "start_off", true );
				args.SetBool( "cycleTrigger", true );
				idEntity* flashEnt = NULL;
				if( gameLocal.SpawnEntityDef( args, &flashEnt, false ) && flashEnt != NULL )
				{
					WeaponParticle_t fpParticle;
					memset( &fpParticle, 0, sizeof( fpParticle ) );
					strcpy( fpParticle.name, "reach_fp_flash" );
					strcpy( fpParticle.particlename, "reach_ar_flash_r15.prt" );
					fpParticle.joint = barrelJointView;
					fpParticle.emitter = static_cast<idFuncEmitter*>( flashEnt );
					renderEntity_t* fpFlash = fpParticle.emitter->GetRenderEntity();
					fpFlash->allowSurfaceInViewID = owner->entityNumber + 1;
					fpFlash->weaponDepthHack = true;
					fpFlash->noShadow = true;
					fpFlash->noOverlays = true;
					fpFlash->shaderParms[6] = 1.0f;
					fpParticle.emitter->BecomeActive( TH_THINK );
					fpParticle.emitter->UpdateVisuals();
					weaponParticles.Set( fpParticle.name, fpParticle );
					weaponSmoke = NULL;
				}
			}
		}

		const idKeyValue* lkv = weaponDef->dict.MatchPrefix( "weapon_light", NULL );
''', path)
    changed[path] = replace(changed[path],
        '\tweaponSmokeStartTime = gameLocal.realClientTime;\n',
        '''	weaponSmokeStartTime = gameLocal.realClientTime;
	WeaponParticle_t* fpFlashParticle = NULL;
	if( weaponParticles.Get( "reach_fp_flash", &fpFlashParticle ) && fpFlashParticle != NULL )
	{
		Event_StartWeaponParticle( "reach_fp_flash" );
	}
''', path)

    # Reach opt-in weapon projection / quick actions. The retail trigger
    # console command is cheat-protected; use gameplay commands plus impulse fallback.
    changed[path] = replace(changed[path],
        'const idEventDef EV_Weapon_UseAmmo( "useAmmo", "d" );',
        'const idEventDef EV_ReachGrenadesAvailable( "reachGrenadesAvailable", NULL, \'f\' );\n'
        'const idEventDef EV_ReachThrowFrag( "reachThrowFrag", NULL, \'f\' );\n'
        'const idEventDef EV_ReachQuickAction( "reachQuickAction", NULL, \'f\' );\n'
        'const idEventDef EV_Weapon_UseAmmo( "useAmmo", "d" );', path)
    changed[path] = replace(changed[path],
        'EVENT( EV_Weapon_UseAmmo,',
        'EVENT( EV_ReachGrenadesAvailable, idWeapon::Event_ReachGrenadesAvailable )\n'
        'EVENT( EV_ReachThrowFrag, idWeapon::Event_ReachThrowFrag )\n'
        'EVENT( EV_ReachQuickAction, idWeapon::Event_ReachQuickAction )\nEVENT( EV_Weapon_UseAmmo,', path)
    changed[path] = replace(changed[path],
        'void idWeapon::Event_EjectBrass()\n',
        (ROOT/'ReachCombat.cpp').read_text() + '\nvoid idWeapon::Event_EjectBrass()\n', path)
    changed[path] = replace(changed[path],
        '\tidDebris* debris = static_cast<idDebris*>( ent );\n\tdebris->Create( owner, origin, axis );',
        '\tidDebris* debris = static_cast<idDebris*>( ent );\n'
        '\tif( ReachCombatWeapon( spawnArgs ) )\n\t{\n'
        '\t\t// Blam ejection-marker rotation is not the stock casing model basis.\n'
        '\t\taxis[0] = -playerViewAxis[1];\n\t\taxis[1] = playerViewAxis[0];\n\t\taxis[2] = playerViewAxis[2];\n\t}\n'
        '\tdebris->Create( owner, origin, axis );', path)
    changed[path] = replace(changed[path],
        '\tlinear_velocity = 40 * ( playerViewAxis[0] + playerViewAxis[1] + playerViewAxis[2] );',
        '\tlinear_velocity = 40 * ( playerViewAxis[0] + playerViewAxis[1] + playerViewAxis[2] );\n'
        '\tif( ReachCombatWeapon( spawnArgs ) )\n\t{\n'
        '\t\t// Camera axis 1 is LEFT. Eject out to the right, slightly upward.\n'
        '\t\tlinear_velocity = -playerViewAxis[1] * 100.0f + playerViewAxis[2] * 12.0f +\n'
        '\t\t\towner->GetPhysics()->GetLinearVelocity();\n\t}', path)
    path = paths[4]
    changed[path] = replace(changed[path], 'public:\n',
        'public:\n\t// Reach opt-in weapon projection / queued SP action API.\n\tbool ReachQueueAction( int action );\n', path)
    changed[path] = replace(changed[path],
        '\tvoid\t\t\t\t\tEvent_EjectBrass();',
        '\t// Reach opt-in weapon projection / single-player grenade inventory events.\n'
        '\tvoid Event_ReachQuickAction();\n'
        '\tvoid Event_ReachGrenadesAvailable();\n\tvoid Event_ReachThrowFrag();\n'
        '\tvoid\t\t\t\t\tEvent_EjectBrass();', path)

    path = paths[5]
    changed[path] = replace(changed[path], '#include "Game_local.h"',
                            '#include "Game_local.h"\n#include "ReachQuickActions.h"', path)
    changed[path] = replace(changed[path], '\tlaunchOrigin = start;\n',
        '\t// Reach opt-in weapon projection / first-floor frag fuse.\n'
        '\tif( idStr::Cmp( GetEntityDefName(), "projectile_reach_frag" ) == 0 && spawnArgs.GetBool( "reach_floor_fuse" ) )\n'
        '\t{\n\t\tspawnArgs.SetInt( "_reach_launchMsec", gameLocal.time );\n'
        '\t\tspawnArgs.SetBool( "_reach_floorBounced", false );\n\t}\n\tlaunchOrigin = start;\n', path)
    changed[path] = replace(changed[path], '\t// direction of projectile\n',
                            (ROOT/'ReachFragCollision.cpp').read_text()+'\t// direction of projectile\n',path)

    path = paths[6]
    changed[path] = replace(changed[path], 'void idGameLocal::InitConsoleCommands()\n',
        (ROOT/'ReachInputCommands.cpp').read_text()+'void idGameLocal::InitConsoleCommands()\n',path)
    changed[path] = replace(changed[path], 'void idGameLocal::InitConsoleCommands()\n{\n',
        'void idGameLocal::InitConsoleCommands()\n{\n'
        '\tcmdSystem->AddCommand( "reachMelee", Cmd_ReachMelee_f, CMD_FL_GAME, "Reach AR melee" );\n'
        '\tcmdSystem->AddCommand( "reachGrenade", Cmd_ReachGrenade_f, CMD_FL_GAME, "Reach AR grenade throw" );\n',path)

    path = paths[7]
    changed[path] = replace(changed[path],
        '\tidVec3\tgunOfs = GunAcceleratingOffset();\n',
        '''\t// Reach opt-in weapon projection / authored first-person movement.
\t// Only this explicitly opted-in SP rifle bypasses Doom's procedural
\t// bob, turn lag, acceleration offset, landing dip and idle drift.
\tconst idWeapon* reachMotionWeapon = weapon.GetEntity();
\tif( !common->IsMultiplayer() && reachMotionWeapon != NULL &&
\t\treachMotionWeapon->spawnArgs.GetBool( "reach_authored_motion" ) &&
\t\tidStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0 &&
\t\tidStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "weapon_scriptobject" ), "weapon_machinegun" ) == 0 )
\t{
\t\torigin = viewOrigin + gunpos * viewAxis;
\t\tidAngles reachViewAngles( independentWeaponPitchAngle, 0.0f, 0.0f );
\t\taxis = ( reachViewAngles.ToMat3() * g_gunScale.GetFloat() ) * viewAxis;
\t\treturn;
\t}
\tidVec3\tgunOfs = GunAcceleratingOffset();
''', path)

    # Validate all changes before touching the source checkout.
    for path in paths:
        if changed[path] == original[path] or MARKER not in changed[path]:
            raise ValueError('Incomplete patch for ' + path)
    helper = root/'neo/renderer/ReachWeaponProjection.h'
    if helper.exists():
        raise FileExistsError('Preserve the existing projection header: ' + str(helper))
    for path in paths:
        (root/path).write_text(changed[path], encoding='utf-8', newline='\n')
    helper.write_bytes((ROOT/'WeaponProjection.h').read_bytes())
    (root/'neo/d3xp/ReachQuickActions.h').write_bytes((ROOT/'ReachQuickActions.h').read_bytes())
    print('Applied projection extension to pinned RBDoom '+UPSTREAM)
    print('Default off; restricted to tagged owner FP rifle/flash; public entity/save/demo formats unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)

