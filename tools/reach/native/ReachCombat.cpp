// Reach opt-in weapon projection / single-player quick-action support.
// No saved fields, new input threads, physics defaults or global ammo changes.
static bool ReachCombatWeapon( const renderEntity_t& ent )
{
	return ent.shaderParms[6] == 1.0f && ent.hModel != NULL &&
		idStr::Cmp( ent.hModel->Name(), "models/md5/weapons/reach_ar/view.md5mesh" ) == 0;
}

void idWeapon::Event_ReachQuickAction()
{
	idThread::ReturnFloat( 0 );
	if( owner == NULL || common->IsMultiplayer() || !ReachCombatWeapon( renderEntity ) ) { return; }
	const int sequence = owner->usercmd.impulseSequence;
	const int previous = spawnArgs.GetInt( "_reach_lastImpulseSequence", "-1" );
	const int action = ReachQuickActions::Read( sequence, previous, owner->usercmd.impulse );
	if( sequence != previous ) { spawnArgs.SetInt( "_reach_lastImpulseSequence", sequence ); }
	if( action != 0 && cvarSystem->GetCVarBool( "g_debugWeapon" ) )
	{
		gameLocal.Printf( "[ReachInput r14] native impulse %d received; sequence=%d\n", owner->usercmd.impulse, sequence );
	}
	idThread::ReturnFloat( action );
}

void idWeapon::Event_ReachGrenadesAvailable()
{
	if( owner == NULL || common->IsMultiplayer() || !ReachCombatWeapon( renderEntity ) )
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
		common->IsClient() || !ReachCombatWeapon( renderEntity ) )
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
