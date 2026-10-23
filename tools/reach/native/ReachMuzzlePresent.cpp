
                        if( weaponDef != NULL && weaponDef->dict.GetBool( "reach_layered_muzzle" ) &&
                            !common->IsMultiplayer() && idStr::Cmpn( part->name, "reach_fp_brake_", 15 ) == 0 )
                        {
                            const int jet = atoi( part->name + 15 );
                            if( jet >= 0 && jet < 5 )
                            {
                                const ReachMuzzle::Jet& source = ReachMuzzle::jets[jet];
                                const idMat3 gunAxis = rendEnt->axis;
                                rendEnt->origin += ( idVec3( source.offset[0], source.offset[1], source.offset[2] ) +
                                    idVec3( 2.0f, -0.6f, 0.0f ) ) * gunAxis;
                                idVec3 direction = idVec3( source.direction[0], source.direction[1], source.direction[2] ) * gunAxis;
                                direction.Normalize();
                                // Parallel-to-direction billboard: preserve the authored jet axis,
                                // and turn only its transverse axis toward this player's camera.
                                idVec3 toCamera = playerViewOrigin - rendEnt->origin;
                                idVec3 side = toCamera.Cross( direction );
                                if( side.Normalize() < .001f ) { side = gunAxis[1]; }
                                rendEnt->axis[0] = direction;
                                rendEnt->axis[1] = side;
                                rendEnt->axis[2] = direction.Cross( side );
                                const float age = ( gameLocal.time - part->startTime ) / 110.0f;
                                // Source centerOffset.y=-.45 anchors a growing jet at its root.
                                rendEnt->origin += direction * ( .9f * 3.9f * 1.35f * ReachMuzzle::BrakeScale( age ) );
                            }
                        }
