    // Reach opt-in weapon projection / M319 source latch and bounce fuse.
    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_m319"))
    {
        idEntity* source=owner.GetEntity();
        idPlayer* player=source!=NULL && source->IsType(idPlayer::Type) ? static_cast<idPlayer*>(source) : NULL;
        // Test-only trigger fixture: SP developer diagnostics can hold one
        // synthetic round without injecting OS input. Ordinary play uses the
        // actual usercmd button exclusively.
        const bool diagnostic=cvarSystem->GetCVarBool("developer") && cvarSystem->GetCVarBool("g_debugWeapon");
        const int testHold=diagnostic ? spawnArgs.GetInt("_m319_test_hold","-1") : -1;
        const bool down=testHold>=0 ? testHold!=0 : (player!=NULL && (player->usercmd.buttons&BUTTON_ATTACK)!=0);
        const bool held=player!=NULL && player->health>0 && down &&
            player->weapon.GetEntity()!=NULL && player->weapon.GetEntity()->spawnArgs.GetBool("reach_m319");
        const int age=gameLocal.time-spawnArgs.GetInt("_m319_launch");
        if(diagnostic) {
            spawnArgs.SetInt("_m319_debugTicks",spawnArgs.GetInt("_m319_debugTicks")+1);
            if(physicsObj.IsAtRest() && !spawnArgs.GetBool("_m319_debugRest")) {
                spawnArgs.SetBool("_m319_debugRest",true);
                gameLocal.Printf("[ReachM319] controller awake at rest age=%d ticks=%d\n",age,spawnArgs.GetInt("_m319_debugTicks"));
            }
        }
        if(physicsObj.IsAtRest() && !spawnArgs.GetBool("_m319_flightStopped")) {
            StopSound(SND_CHANNEL_BODY,false);spawnArgs.SetBool("_m319_flightStopped",true);
        }

        const idVec3 previous=spawnArgs.GetVector("_m319_prev");
        const float oldDistance=spawnArgs.GetFloat("_m319_distance");
        const float travelled=oldDistance+(GetPhysics()->GetOrigin()-previous).Length();
        if(!spawnArgs.GetBool("_m319_bounced")) {
            const float desired=ReachM319::FlightSpeed(travelled);
            idVec3 velocity=GetPhysics()->GetLinearVelocity();idVec3 direction=velocity;direction.Normalize();
            velocity+=direction*(desired-ReachM319::FlightSpeed(oldDistance));GetPhysics()->SetLinearVelocity(velocity);
        }
        spawnArgs.SetFloat("_m319_distance",travelled);spawnArgs.SetVector("_m319_prev",GetPhysics()->GetOrigin());
        if(travelled>=12000) {Event_Explode();return;}
        const int old=spawnArgs.GetInt("_m319_latch");
        const int mode=ReachM319::Step(old,held,age,spawnArgs.GetBool("_m319_bounced"));
        spawnArgs.SetInt("_m319_latch",mode);
        if(player!=NULL && player->weapon.GetEntity()!=NULL && player->weapon.GetEntity()->spawnArgs.GetBool("reach_m319")) {
            idWeapon* gun=player->weapon.GetEntity();
            gun->spawnArgs.SetInt("_m319_displayUntil",gameLocal.time+100);
            gun->spawnArgs.SetBool("_m319_displayTether",mode==ReachM319::Holding || mode==ReachM319::Armed);
            const int status=mode==ReachM319::Holding ? 1 : mode==ReachM319::Armed ?
                (spawnArgs.GetBool("_m319_bounced") ? (GetPhysics()->GetLinearVelocity().Length()<50 ? 4 : 3) : 2) : 0;
            gun->spawnArgs.SetInt("_m319_status",status);
            gun->spawnArgs.SetFloat("_m319_range",(GetPhysics()->GetOrigin()-player->GetPhysics()->GetOrigin()).Length()/39.3700787f);
        }
        if(mode==ReachM319::Remote)
        {
            if(player!=NULL && player->weapon.GetEntity()!=NULL && player->weapon.GetEntity()->spawnArgs.GetBool("reach_m319")) {
                player->weapon.GetEntity()->spawnArgs.SetInt("_m319_status",5);
                player->weapon.GetEntity()->spawnArgs.SetInt("_m319_displayUntil",gameLocal.time+300);
            }
            trace_t remote;memset(&remote,0,sizeof(remote));remote.endpos=GetPhysics()->GetOrigin();remote.endAxis=GetPhysics()->GetAxis();
            remote.c.normal=-physicsObj.GetGravityNormal();remote.c.entityNum=ENTITYNUM_WORLD;
            if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachM319] remote explosive age=%d\n",age);
            Explode(remote,NULL);return;
        }
        if(mode==ReachM319::Normal && spawnArgs.GetBool("_m319_bounced") && !spawnArgs.GetBool("_m319_fusePosted")) {
            spawnArgs.SetBool("_m319_fusePosted",true);CancelEvents(&EV_Explode);
            PostEventMS(&EV_Explode,ReachM319::RemainingFuse(gameLocal.time,spawnArgs.GetInt("_m319_bounce")));
        }
        if(age>=45000) {Fizzle();return;} // Lost/out-of-map projectiles cannot accumulate indefinitely.
    }
