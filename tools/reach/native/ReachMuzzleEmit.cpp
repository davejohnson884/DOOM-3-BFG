
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
