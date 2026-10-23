
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
