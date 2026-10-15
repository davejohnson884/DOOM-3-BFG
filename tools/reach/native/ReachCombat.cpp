// Reach opt-in weapon projection / single-player quick-action support.
// No saved fields, new input threads, physics defaults or global ammo changes.
static bool ReachCombatWeapon( const idDict& args )
{
	// Gameplay identity must not depend on render-model cache names or shader state.
	return idStr::Cmp( args.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0 &&
		idStr::Cmp( args.GetString( "weapon_scriptobject" ), "weapon_machinegun" ) == 0;
}

bool idWeapon::ReachQueueAction( int action )
{
	if( owner == NULL || owner->health <= 0 || common->IsMultiplayer() ||
		!ReachCombatWeapon( spawnArgs ) || ( action != 1 && action != 2 ) ) { return false; }
	spawnArgs.SetInt( "_reach_pendingAction", action );
	if( cvarSystem->GetCVarBool( "g_debugWeapon" ) )
	{
		gameLocal.Printf( "[ReachInput r15] gameplay command queued: %s\n", action == 1 ? "melee" : "grenade" );
	}
	return true;
}

void idWeapon::Event_ReachQuickAction()
{
	idThread::ReturnFloat( 0 );
	if( owner == NULL || common->IsMultiplayer() || !ReachCombatWeapon( spawnArgs ) ) { return; }
	if( cvarSystem->GetCVarBool( "g_debugWeapon" ) && !spawnArgs.GetBool( "_reach_inputReported" ) )
	{
		spawnArgs.SetBool( "_reach_inputReported", true );
		gameLocal.Printf( "[ReachInput r15] gameplay identity accepted; model=%s parm6=%.3f\n",
			renderEntity.hModel != NULL ? renderEntity.hModel->Name() : "<none>", renderEntity.shaderParms[6] );
	}
	const int sequence = owner->usercmd.impulseSequence;
	const int previous = spawnArgs.GetInt( "_reach_lastImpulseSequence", "-1" );
	const int pending = spawnArgs.GetInt( "_reach_pendingAction", "0" );
	spawnArgs.SetInt( "_reach_pendingAction", 0 );
	const int action = pending != 0 ? pending : ReachQuickActions::Read( sequence, previous, owner->usercmd.impulse );
	if( sequence != previous ) { spawnArgs.SetInt( "_reach_lastImpulseSequence", sequence ); }
	if( action != 0 && cvarSystem->GetCVarBool( "g_debugWeapon" ) )
	{
		gameLocal.Printf( "[ReachInput r15] weapon consumed action=%d; impulse=%d sequence=%d\n", action, owner->usercmd.impulse, sequence );
	}
	idThread::ReturnFloat( action );
}

void idWeapon::Event_ReachGrenadesAvailable()
{
	if( owner == NULL || common->IsMultiplayer() || !ReachCombatWeapon( spawnArgs ) )
	{
		idThread::ReturnFloat( 0 );
		return;
	}
	const ammo_t type = owner->inventory.AmmoIndexForAmmoClass( "ammo_grenades" );
	idThread::ReturnFloat( type == 0 ? 0 : owner->inventory.HasAmmo( type, 1 ) );
}

void idWeapon::Event_ReachThrowFrag()
{
	idThread::ReturnFloat( 0 );
	if( owner == NULL || owner->health <= 0 || common->IsMultiplayer() ||
		common->IsClient() || !ReachCombatWeapon( spawnArgs ) )
	{
		return;
	}
	const ammo_t type = owner->inventory.AmmoIndexForAmmoClass( "ammo_grenades" );
	if( type == 0 || owner->inventory.HasAmmo( type, 1 ) == 0 ) { return; }
	const idDeclEntityDef* fragDef = gameLocal.FindEntityDef( "projectile_reach_frag", false );
	if( fragDef == NULL ) { return; }
	idEntity* ent = NULL;
	if( !gameLocal.SpawnEntityDef( fragDef->dict, &ent, false ) || ent == NULL ) { return; }
	if( !ent->IsType( idProjectile::Type ) )
	{
		ent->PostEventMS( &EV_Remove, 0 );
		return;
	}
	idProjectile* frag = static_cast<idProjectile*>( ent );
	const idVec3 direction = playerViewAxis[0];
	frag->Create( owner, playerViewOrigin, direction );
	const idVec3 desired = playerViewOrigin + playerViewAxis[0] * 18.0f +
		playerViewAxis[1] * 5.0f - playerViewAxis[2] * 6.0f;
	trace_t trace;
	gameLocal.clip.Translation( trace, playerViewOrigin, desired,
		frag->GetPhysics()->GetClipModel(), frag->GetPhysics()->GetAxis(), MASK_SHOT_RENDERMODEL, owner );
	// Do not release the projectile in a wall, or consume ammo for a failed spawn.
	if( trace.fraction <= 0.0f || !owner->inventory.UseAmmo( type, 1 ) )
	{
		frag->PostEventMS( &EV_Remove, 0 );
		return;
	}
	frag->Launch( trace.endpos, direction, owner->GetPhysics()->GetLinearVelocity() );
	idThread::ReturnFloat( 1 );
}
