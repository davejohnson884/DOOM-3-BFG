    // Reach opt-in weapon projection / M319 source latch and bounce fuse.
    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_m319"))
    {
        idEntity* source=owner.GetEntity();
        idPlayer* player=source!=NULL && source->IsType(idPlayer::Type) ? static_cast<idPlayer*>(source) : NULL;
        const bool held=player!=NULL && player->health>0 && (player->usercmd.buttons&BUTTON_ATTACK)!=0 &&
            player->weapon.GetEntity()!=NULL && player->weapon.GetEntity()->spawnArgs.GetBool("reach_m319");
        const int age=gameLocal.time-spawnArgs.GetInt("_m319_launch");
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
            spawnArgs.Set("def_splash_damage",spawnArgs.GetString("def_m319_tethered_damage","damage_reach_m319_tethered"));
            spawnArgs.Set("model_detonate",spawnArgs.GetString("model_m319_emp","reach_m319_emp.prt"));
            spawnArgs.Set("explode_light_color",".15 .55 1");
            if(player!=NULL && player->weapon.GetEntity()!=NULL && player->weapon.GetEntity()->spawnArgs.GetBool("reach_m319")) {
                player->weapon.GetEntity()->spawnArgs.SetInt("_m319_status",5);
                player->weapon.GetEntity()->spawnArgs.SetInt("_m319_displayUntil",gameLocal.time+300);
            }
            // Shield/vehicle EMP has no universal Doom counterpart. Apply its
            // separate source electrical damage to campaign machines only;
            // ordinary enemies receive the source tethered blast below.
            for(idEntity* target=gameLocal.spawnedEntities.Next();target!=NULL;target=target->spawnNode.Next()) {
                const char* name=target->GetEntityDefName();
                if(target==source || !target->fl.takedamage || (strstr(name,"sentry")==NULL && strstr(name,"turret")==NULL)) continue;
                idVec3 delta=target->GetPhysics()->GetOrigin()-GetPhysics()->GetOrigin();
                const float distance=delta.Normalize();idVec3 hit;
                if(distance<300 && target->CanDamage(GetPhysics()->GetOrigin(),hit))
                    target->Damage(this,source,delta,"damage_reach_m319_emp",1.0f-distance/300.0f,INVALID_JOINT);
            }
            trace_t remote;memset(&remote,0,sizeof(remote));remote.endpos=GetPhysics()->GetOrigin();remote.endAxis=GetPhysics()->GetAxis();
            remote.c.normal=-physicsObj.GetGravityNormal();remote.c.entityNum=ENTITYNUM_WORLD;
            if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachM319] remote EMP age=%d\n",age);
            Explode(remote,NULL);return;
        }
        if(mode==ReachM319::Normal && spawnArgs.GetBool("_m319_bounced") && !spawnArgs.GetBool("_m319_fusePosted")) {
            spawnArgs.SetBool("_m319_fusePosted",true);CancelEvents(&EV_Explode);
            PostEventMS(&EV_Explode,ReachM319::RemainingFuse(gameLocal.time,spawnArgs.GetInt("_m319_bounce")));
        }
        if(age>=45000) {Fizzle();return;} // Lost/out-of-map projectiles cannot accumulate indefinitely.
    }
