					// Reach opt-in weapon projection: seed shared, world-space smoke
					// at the apparent FP muzzle, then leave already emitted puffs free.
					if( !common->IsMultiplayer() && spawnArgs.GetBool( "reach_native_muzzle_fx" ) &&
						idStr::Cmp( part->name, "reach_barrel_smoke" ) == 0 &&
						idStr::Cmp( spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0 &&
						idStr::Cmp( spawnArgs.GetString( "weapon_scriptobject" ), "weapon_machinegun" ) == 0 )
					{
						muzzleOrigin += idVec3( 2.0f, -0.6f, 0.0f ) * muzzleAxis;
						const renderView_t* view = owner->GetRenderView();
						if( view != NULL )
						{
							const float scale = ReachMuzzle::WorldSmokeScale(
								cvarSystem->GetCVarFloat( "r_reachWeaponFov" ), view->fov_y );
							const idVec3 delta = muzzleOrigin - playerViewOrigin;
							muzzleOrigin = playerViewOrigin + ( delta * playerViewAxis[0] ) * playerViewAxis[0] +
								scale * ( ( delta * playerViewAxis[1] ) * playerViewAxis[1] +
								( delta * playerViewAxis[2] ) * playerViewAxis[2] );
						}
					}
