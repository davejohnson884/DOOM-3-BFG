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
             'neo/d3xp/gamesys/SysCmds.cpp', 'neo/d3xp/Player.cpp', 'neo/d3xp/SmokeParticles.cpp']
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
                            '#include "Game_local.h"\n#include "ReachQuickActions.h"\n#include "ReachMuzzleEffects.h"\n'
                            'static bool ReachCombatWeapon( const idDict& args );', path)
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
		if( ( weaponDef != NULL && weaponDef->dict.GetBool( "reach_native_muzzle_fx" ) ) && fpFlashParticle->emitter != NULL )
		{
			renderEntity_t* flash = fpFlashParticle->emitter->GetRenderEntity();
			flash->shaderParms[5] = float( gameLocal.random.RandomInt( 8 ) );
			fpFlashParticle->emitter->UpdateVisuals();
		}
		Event_StartWeaponParticle( "reach_fp_flash" );
		if( ( weaponDef != NULL && weaponDef->dict.GetBool( "reach_native_muzzle_fx" ) ) )
		{
			WeaponParticle_t* smoke = NULL;
			if( !weaponParticles.Get( "reach_barrel_smoke", &smoke ) || smoke == NULL )
			{
				// Existing saves may predate the smoke registration in the def.
				WeaponParticle_t restoredSmoke;
				memset( &restoredSmoke, 0, sizeof( restoredSmoke ) );
				strcpy( restoredSmoke.name, "reach_barrel_smoke" );
				strcpy( restoredSmoke.particlename, "reach_barrel_smoke_native.prt" );
				restoredSmoke.joint = barrelJointView;
				restoredSmoke.smoke = true;
				restoredSmoke.particle = static_cast<const idDeclParticle*>( declManager->FindType( DECL_PARTICLE, restoredSmoke.particlename, false ) );
				weaponParticles.Set( restoredSmoke.name, restoredSmoke );
			}
			Event_StartWeaponParticle( "reach_barrel_smoke" );
            weaponParticles.Get( "reach_barrel_smoke", &smoke );

            // Emit on the shot's simulation tick. This avoids both the draw-only
            // PresentWeapon path and mismatched slow/fast clock timestamps.
            if( smoke != NULL )
            {
                smoke->active = false;
                SetTimeState smokeClock( timeGroup );
                idVec3 smokeOrigin;
                idMat3 smokeAxis;
                GetGlobalJointTransform( true, barrelJointView, smokeOrigin, smokeAxis );
                smokeOrigin += idVec3( 2.0f, -0.6f, 0.0f ) * smokeAxis;
                const renderView_t* view = owner->GetRenderView();
                if( view != NULL )
                {
                    const float scale = ReachMuzzle::WorldSmokeScale( cvarSystem->GetCVarFloat( "r_reachWeaponFov" ), view->fov_y );
                    const idVec3 delta = smokeOrigin - playerViewOrigin;
                    smokeOrigin = playerViewOrigin + ( delta * playerViewAxis[0] ) * playerViewAxis[0] +
                        scale * ( ( delta * playerViewAxis[1] ) * playerViewAxis[1] + ( delta * playerViewAxis[2] ) * playerViewAxis[2] );
                }
                if( gameLocal.isNewFrame )
                {
                    gameLocal.smokeParticles->EmitSmoke( smoke->particle, gameLocal.time,
                        gameLocal.random.RandomFloat(), smokeOrigin, smokeAxis, timeGroup );
                }
            }


            if( weaponDef->dict.GetBool( "reach_layered_muzzle" ) )
            {
                for( int jet = 0; jet < 5; ++jet )
                {
                    const idStr name = va( "reach_fp_brake_%d", jet );
                    WeaponParticle_t* brake = NULL;
                    if( !weaponParticles.Get( name.c_str(), &brake ) || brake == NULL )
                    {
                        const idDeclEntityDef* def = gameLocal.FindEntityDef( "func_emitter", false );
                        if( def == NULL ) { continue; }
                        idDict args = def->dict;
                        args.Set( "model", "reach_ar_brake_native.prt" );
                        args.SetBool( "start_off", true );
                        args.SetBool( "cycleTrigger", true );
                        idEntity* ent = NULL;
                        if( !gameLocal.SpawnEntityDef( args, &ent, false ) || ent == NULL ) { continue; }
                        WeaponParticle_t entry;
                        memset( &entry, 0, sizeof( entry ) );
                        strcpy( entry.name, name.c_str() );
                        strcpy( entry.particlename, "reach_ar_brake_native.prt" );
                        entry.joint = barrelJointView;
                        entry.emitter = static_cast<idFuncEmitter*>( ent );
                        renderEntity_t* re = entry.emitter->GetRenderEntity();
                        re->allowSurfaceInViewID = owner->entityNumber + 1;
                        re->weaponDepthHack = true;
                        re->noShadow = re->noOverlays = true;
                        re->shaderParms[6] = 1.0f;
                        entry.emitter->BecomeActive( TH_THINK );
                        weaponParticles.Set( name.c_str(), entry );
                        weaponParticles.Get( name.c_str(), &brake );
                    }
                    if( brake != NULL && brake->emitter != NULL )
                    {
                        // Pick a source sprite/mirror at birth, not a new star shape each frame.
                        brake->emitter->GetRenderEntity()->shaderParms[5] = float( gameLocal.random.RandomInt( 8 ) );
                        Event_StartWeaponParticle( name.c_str() );
                    }
                }
            }

		}
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
        (ROOT/'ReachCombat.cpp').read_text() + '\n' + (ROOT/'ReachCamera.cpp').read_text() +
        '\nvoid idWeapon::Event_EjectBrass()\n', path)
    changed[path] = replace(changed[path], 'void idWeapon::Clear()\n{\n',
        'void idWeapon::Clear()\n{\n\t// Reach opt-in weapon projection / transient camera state.\n\treachCamera.Reset();\n',path)
    changed[path] = replace(changed[path], '\tweaponSmokeStartTime = gameLocal.realClientTime;\n',
        '\tweaponSmokeStartTime = gameLocal.realClientTime;\n'
        '\tif( ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_authored_motion") )\n'
        '\t{\n\t\tSetTimeState cameraShotClock(timeGroup);\n\t\treachCamera.Shot(gameLocal.time);\n\t}\n',path)
    changed[path] = replace(changed[path],
        '\tidDebris* debris = static_cast<idDebris*>( ent );\n\tdebris->Create( owner, origin, axis );',
        '\tidDebris* debris = static_cast<idDebris*>( ent );\n'
        '\tif( ReachCombatWeapon( spawnArgs ) )\n\t{\n'
        '\t\t// Blam ejection-marker rotation is not the stock casing model basis.\n'
        '\t\taxis[0] = -playerViewAxis[1];\n\t\taxis[1] = playerViewAxis[0];\n\t\taxis[2] = playerViewAxis[2];\n'
        '\t\t// Source particle starts quarter-turned; vary the initial lean slightly.\n'
        '\t\taxis = idAngles(-90.0f+15.0f*gameLocal.random.CRandomFloat(),0,8.0f*gameLocal.random.CRandomFloat()).ToMat3()*axis;\n\t}\n'
        + (ROOT/'ReachCasingOrigin.cpp').read_text() +
        '\tdebris->Create( owner, origin, axis );', path)
    changed[path] = replace(changed[path],
        '\tlinear_velocity = 40 * ( playerViewAxis[0] + playerViewAxis[1] + playerViewAxis[2] );',
        '\tlinear_velocity = 40 * ( playerViewAxis[0] + playerViewAxis[1] + playerViewAxis[2] );\n'
        '\tif( ReachCombatWeapon( spawnArgs ) )\n\t{\n'
        '\t\t// Retarget the original marker into the lower, outward reference arc.\n'
        '\t\t// Preserve source launch speed; vary direction independently for each case.\n'
        '\t\tidVec3 direction = playerViewAxis[0]*((reachEjectDirection*playerViewAxis[0])+0.035f*gameLocal.random.CRandomFloat()) -\n'
        '\t\t\tplayerViewAxis[1]*(-(reachEjectDirection*playerViewAxis[1])*1.15f+0.06f*gameLocal.random.CRandomFloat()) +\n'
        '\t\t\tplayerViewAxis[2]*((reachEjectDirection*playerViewAxis[2])*0.35f+0.035f*gameLocal.random.CRandomFloat());\n'
        '\t\tdirection.Normalize();\n'
        '\t\tlinear_velocity = direction*(300.0f+60.0f*gameLocal.random.RandomFloat()) +\n'
        '\t\t\towner->GetPhysics()->GetLinearVelocity();\n\t}', path)
    changed[path] = replace(changed[path],
        '\tdebris->GetPhysics()->SetAngularVelocity( angular_velocity );\n',
        '\tif( ReachCombatWeapon(spawnArgs) )\n\t{\n'
        '\t\t// Source initial rotation rate spans -5..5 turns/s. Favor visible end-over-end tumble.\n'
        '\t\tangular_velocity = playerViewAxis[0]*(31.4159265f*gameLocal.random.CRandomFloat()) +\n'
        '\t\t\tplayerViewAxis[1]*(4.0f*gameLocal.random.CRandomFloat()) + playerViewAxis[2]*(4.0f*gameLocal.random.CRandomFloat());\n\t}\n'
        '\tdebris->GetPhysics()->SetAngularVelocity( angular_velocity );\n' +
        (ROOT/'ReachCasingDebug.cpp').read_text(),path)

    changed[path] = replace(changed[path],
        '\tgameLocal.SpawnEntityDef( brassDict, &ent, false );',
        '\tconst idVec3 reachEjectDirection = axis[0];\n\tgameLocal.SpawnEntityDef( brassDict, &ent, false );', path)

    # Reach opt-in weapon projection / original five directional brake jets.
    changed[path] = replace(changed[path],
        '\t\t\t\t\t\tGetGlobalJointTransform( true, part->joint, rendEnt->origin, rendEnt->axis );\n',
        '\t\t\t\t\t\tGetGlobalJointTransform( true, part->joint, rendEnt->origin, rendEnt->axis );\n' +
        (ROOT/'ReachMuzzlePresent.cpp').read_text(), path)

    # Reach opt-in weapon projection / world-space barrel smoke.
    changed[path] = replace(changed[path],
        '\t\t\t\t\tif( !gameLocal.smokeParticles->EmitSmoke( part->particle, part->startTime, gameLocal.random.RandomFloat(), muzzleOrigin, muzzleAxis, timeGroup /*_D3XP*/ ) )\n',
        (ROOT/'ReachMuzzleSmoke.cpp').read_text() +
        '\t\t\t\t\tif( !gameLocal.smokeParticles->EmitSmoke( part->particle, part->startTime, gameLocal.random.RandomFloat(), muzzleOrigin, muzzleAxis, timeGroup /*_D3XP*/ ) )\n', path)

    path = paths[4]
    changed[path] = replace(changed[path], 'class idWeapon : public idAnimatedEntity\n',
        '#include "ReachCameraMotion.h"\n\nclass idWeapon : public idAnimatedEntity\n',path)
    changed[path] = replace(changed[path], 'public:\n',
        'public:\n\t// Reach opt-in weapon projection / queued SP action API.\n\tbool ReachQueueAction( int action );\n'
        '\tbool ReachCameraMotion( idVec3& offset, idAngles& angles );\n'
        'private:\n\tReachCamera::State reachCamera; // transient; resets on Clear/restore construction\npublic:\n', path)
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
        '\t\torigin += axis[0] * g_viewNodalX.GetFloat() + axis[2] * g_viewNodalZ.GetFloat();\n',
        '''\t\torigin += axis[0] * g_viewNodalX.GetFloat() + axis[2] * g_viewNodalZ.GetFloat();
        // Reach opt-in weapon projection / animation camera.
        // The camera and FP weapon share this view frame. Input viewAngles are
        // never modified, so action/recoil recovery cannot accumulate aim drift.
        idWeapon* reachCameraWeapon=weapon.GetEntity();
        if( !common->IsMultiplayer() && !spectating && !gameLocal.inCinematic &&
            privateCameraView==NULL && gameLocal.GetCamera()==NULL &&
            !pm_thirdPerson.GetBool() && !pm_thirdPersonDeath.GetBool() && reachCameraWeapon!=NULL )
        {
            idVec3 cameraOffset;idAngles cameraAngles;
            if( reachCameraWeapon->ReachCameraMotion(cameraOffset,cameraAngles) )
            {
                origin+=cameraOffset*axis;
                axis=cameraAngles.ToMat3()*axis;
            }
        }
        // Reach animation camera end.
''',path)
    changed[path] = replace(changed[path],
        '\tidVec3\tgunOfs = GunAcceleratingOffset();\n',
        '''\t// Reach opt-in weapon projection / authored first-person movement.
\t// Only this explicitly opted-in SP rifle bypasses Doom's procedural
\t// bob, turn lag, acceleration offset, landing dip and idle drift.
\tidWeapon* reachMotionWeapon = weapon.GetEntity();
\tif( !common->IsMultiplayer() && reachMotionWeapon != NULL &&
\t\treachMotionWeapon->spawnArgs.GetBool( "reach_authored_motion" ) &&
\t\tidStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0 &&
\t\tidStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "weapon_scriptobject" ), "weapon_machinegun" ) == 0 )
\t{
\t\t// Publish exact contact state to the existing script key interface.
\t\treachMotionWeapon->spawnArgs.SetInt( "_reach_motion_grounded", physicsObj.HasGroundContacts() ? 1 : -1 );
\t\torigin = viewOrigin + gunpos * viewAxis;
\t\tidAngles reachViewAngles( independentWeaponPitchAngle, 0.0f, 0.0f );
\t\taxis = ( reachViewAngles.ToMat3() * g_gunScale.GetFloat() ) * viewAxis;
\t\treturn;
\t}
\tidVec3\tgunOfs = GunAcceleratingOffset();
''', path)

    # Reach opt-in weapon projection / diagnostic emission evidence (default off).
    path = paths[8]
    changed[path] = replace(changed[path], '\t\t\tnumActiveSmokes++;\n',
        '\t\t\tnumActiveSmokes++;\n' + '            // Reach opt-in weapon projection / emission diagnostics, default off.\n            if( cvarSystem->GetCVarBool( "reach_fxDebug" ) && stage->material != NULL &&\n                idStr::Cmp( stage->material->GetName(), "reach/muzzle_smoke_soft" ) == 0 )\n            {\n                cvarSystem->SetCVarInteger( "reach_fxSmokeEmitted", cvarSystem->GetCVarInteger( "reach_fxSmokeEmitted" ) + 1 );\n            }\n', path)

    # Data-driven Magnum shares existing controller without changing script/save bytecode.
    from magnum_support import extend
    changed = extend(changed, replace)
    from shotgun_support import extend as shotgun_extend
    changed = shotgun_extend(changed, replace)
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
    (root/'neo/d3xp/ReachMuzzleEffects.h').write_bytes((ROOT/'MuzzleEffects.h').read_bytes())
    (root/'neo/d3xp/ReachCameraMotion.h').write_bytes((ROOT/'CameraMotion.h').read_bytes())
    (root/'neo/d3xp/ReachWeaponActions.h').write_bytes((ROOT/'WeaponActions.h').read_bytes())
    print('Applied projection extension to pinned RBDoom '+UPSTREAM)
    print('Default off; restricted to tagged owner FP rifle/flash; public entity/save/demo formats unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)



