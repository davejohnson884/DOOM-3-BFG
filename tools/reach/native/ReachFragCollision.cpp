	// Reach opt-in weapon projection / source-tag frag fuse. The source timer
	// starts after a floor bounce and may not detonate before its arming time.
	// Per-instance spawn args are already saved by idEntity; no new save fields.
	if( !common->IsMultiplayer() && idStr::Cmp( GetEntityDefName(), "projectile_reach_frag" ) == 0 &&
		spawnArgs.GetBool( "reach_floor_fuse" ) && !spawnArgs.GetBool( "_reach_floorBounced" ) &&
		!ent->IsType( idActor::Type ) && !ent->IsType( idAFAttachment::Type ) &&
		collision.c.normal * -physicsObj.GetGravityNormal() >= 0.5f )
	{
		spawnArgs.SetBool( "_reach_floorBounced", true );
		const int arming = SEC2MS( spawnArgs.GetFloat( "reach_arming_time", "1.4" ) );
		const float minimum = spawnArgs.GetFloat( "reach_bounce_timer_min", "0.6" );
		const float maximum = spawnArgs.GetFloat( "reach_bounce_timer_max", "0.65" );
		const int timer = SEC2MS( minimum + ( maximum - minimum ) * gameLocal.random.RandomFloat() );
		const int delay = ReachQuickActions::BounceFuseDelay( gameLocal.time,
			spawnArgs.GetInt( "_reach_launchMsec" ), arming, timer );
		CancelEvents( &EV_Fizzle );
		CancelEvents( &EV_Explode );
		PostEventMS( &EV_Explode, delay );
	}

