"""Needle Rifle opt-in. Existing entity dictionaries/bind/events carry save state."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';w=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_needle_rifle')+' )')
 fplayer='neo/d3xp/Player.cpp';p=changed[fplayer]
 expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
 assert expr in p;changed[fplayer]=p.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_needle_rifle')+' )')
 anchor='\tassert( modelname );\n';w=replace(w,anchor,anchor+'    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_rifle") && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) modelname="viewmodel_reach_needle_rifle_present";\n',f)
 anchor='\tammoClip = ammoinclip;\n';w=replace(w,anchor,'''    if(!common->IsMultiplayer() && weaponDef->dict.GetBool("reach_needle_rifle") && ammoinclip>clipSize) {
        const int reserve=owner->inventory.GetInventoryAmmoForType(ammoType);
        if(reserve>=0) owner->inventory.SetInventoryAmmoForType(ammoType,reserve+ammoinclip-clipSize);
        ammoinclip=clipSize;
    }
'''+anchor,f)
 anchor='void idWeapon::PresentWeapon( bool showViewModel )\n{\n';w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && weaponDef!=NULL &&
       idStr::Cmp(weaponDef->GetName(),"weapon_chaingun")==0 && weaponDef->dict.GetBool("reach_needle_rifle") &&
       !spawnArgs.GetBool("reach_needle_rifle")) {
        const int loaded=ammoClip.Get();GetWeaponDef("weapon_chaingun",loaded);
        gameLocal.Printf("[ReachNeedle] legacy chaingun/M37 migrated; clip=%d reserve=%d\\n",ammoClip.Get(),owner->inventory.GetInventoryAmmoForType(ammoType));
    }
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_rifle")) {
        if(owner!=NULL && owner->health>0 && !gameLocal.inCinematic) {
            const bool zoomDown=(owner->usercmd.buttons&BUTTON_ZOOM)!=0;
            if(zoomDown!=spawnArgs.GetBool("_nr_zoomDown")) {
                StartSound(zoomDown ? "snd_reach_zoom_in" : "snd_reach_zoom_out",SND_CHANNEL_ITEM,0,false,NULL);
                spawnArgs.SetBool("_nr_zoomDown",zoomDown);
            }
        }
        // These material parameters are private to the Needle Rifle. Source
        // ammo-function frames control the visible bank independently of recoil.
        const float remaining=idMath::ClampFloat(0,1,float(ammoClip.Get())/21.0f);
        renderEntity.shaderParms[8]=remaining*13.0f;
        if(worldModel.GetEntity()!=NULL) worldModel.GetEntity()->SetShaderParm(8,remaining*13.0f);
        const idAnimBlend* a=animator.CurrentAnim(ANIMCHANNEL_ALL);
        const bool reload=a!=NULL && strstr(a->AnimFullName(),"reload")!=NULL;
        const float age=reload ? a->AnimTime(gameLocal.time)/1000.0f : 0;
        renderEntity.shaderParms[7]=reload ? idMath::ClampFloat(0,1,(age-.45f)*5)*idMath::ClampFloat(0,1,(2.1f-age)*5) : 0;
    }
''',f)
 anchor='void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{\n';w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_rifle") && channel==ANIMCHANNEL_ALL) {
        if(strstr(animname,"reload")!=NULL) spawnArgs.SetFloat("reach_reload_fill_time",48.0f/30.0f);
        if(idStr::Cmp(animname,"fire")==0) {
            const int variant=spawnArgs.GetInt("_nr_fireVariant")%3+1;
            spawnArgs.SetInt("_nr_fireVariant",variant);
            animname=variant==1 ? "fire_a" : variant==2 ? "fire_b" : "fire_c";
        }
        if(idStr::Cmp(animname,"melee")==0) animname="melee1";
    }
''',f)
 anchor='int\tidWeapon::GetZoomFov()\n{\n';w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_needle_rifle"))
        return idMath::Ftoi(RAD2DEG(2*idMath::ATan(idMath::Tan(DEG2RAD(owner->DefaultFov()*.5f))/2.0f)));
''',f)
 # Original single-wield barrel-error functions. Unlike the shared AR bloom,
 # these add a nonlinear shot penalty and recover over .9 seconds.
 anchor='    spread=ReachM37Spread(spread);\n'
 w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_needle_rifle")) {
        const int previous=spawnArgs.GetInt("_nr_lastShot","-1");
        float error=spawnArgs.GetFloat("_nr_error");
        if(previous>=0 && gameLocal.time>=previous) error-=float(gameLocal.time-previous)/900.0f;
        error=idMath::ClampFloat(0,1,error);
        spread=(.15f+1.85f*error)/((owner->usercmd.buttons&BUTTON_ZOOM) ? 2.0f : 1.0f);
        const float penalty=owner->AI_CROUCH ?
            (error<.2f ? 2.0f*error+.35f : -.6875f*error+.8875f) :
            (error<.15f ? 3.3333333f*error+.35f : -.7647059f*error+.9647059f);
        spawnArgs.SetFloat("_nr_error",idMath::ClampFloat(0,1,error+penalty));
        spawnArgs.SetInt("_nr_lastShot",gameLocal.time);
        if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachNeedle] SHOT time=%d error=%.5f spread=%.5f\\n",gameLocal.time,error,spread);
    }
''',f)
 changed[f]=w
 f='neo/d3xp/Projectile.cpp';p=changed[f]
 anchor='void idProjectile::Think()\n{\n';p=replace(p,anchor,anchor+'''    // Reach opt-in weapon projection / attached crystal lifecycle. Bind state,
    // absolute deadlines and target spawn IDs already use the public save ABI.
    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_needle_shard") && spawnArgs.GetBool("_nr_attached")) {
        const int combineAt=spawnArgs.GetInt("_nr_superAt");
        const int expireAt=spawnArgs.GetInt("_nr_expireAt");
        if(combineAt>0 && gameLocal.time>=combineAt) {
            if(spawnArgs.GetBool("_nr_consumed")) {Fizzle();return;}
            idEntityPtr<idEntity> target;target.SetSpawnId(spawnArgs.GetInt("_nr_target"));
            idEntity* victim=target.GetEntity();
            const idVec3 position=physicsObj.GetOrigin();
            Unbind();spawnArgs.SetBool("_nr_super",true);
            if(victim!=NULL && victim->fl.takedamage && victim->health>0)
                victim->Damage(this,owner.GetEntity(),vec3_zero,spawnArgs.GetString("def_attached_super"),damagePower,INVALID_JOINT);
            trace_t impact;memset(&impact,0,sizeof(impact));impact.endpos=position;impact.endAxis=physicsObj.GetAxis();impact.c.normal.Set(0,0,1);
            Explode(impact,victim);
            if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachNeedle] SUPER time=%d target=%d\\n",gameLocal.time,victim!=NULL ? victim->entityNumber : -1);
            return;
        }
        if(expireAt>0 && gameLocal.time>=expireAt) {
            Unbind();trace_t impact;memset(&impact,0,sizeof(impact));impact.endpos=physicsObj.GetOrigin();impact.endAxis=physicsObj.GetAxis();impact.c.normal.Set(0,0,1);
            Explode(impact,NULL);return;
        }
    }
''',f)
 # The ordinary direct-hit path retains Doom damage groups, bleeding, powerups
 # and campaign Killed callbacks. Attach only after that path has run.
 start=p.index('bool idProjectile::Collide(');end=p.index('void idProjectile::AddDefaultDamageEffect',start)
 body=p[start:end];anchor='\tExplode( collision, ignore );\n'
 body=replace(body,'\tdamageDefName = spawnArgs.GetString( \"def_damage\" );\n','''\tdamageDefName = spawnArgs.GetString( "def_damage" );
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_shard")) {
        idEntity* damagedActor=ent;
        if(ent->IsType(idAFAttachment::Type)) damagedActor=static_cast<idAFAttachment*>(ent)->GetBody();
        idActor* actor=damagedActor!=NULL && damagedActor->IsType(idActor::Type) ? static_cast<idActor*>(damagedActor) : NULL;
        if(actor!=NULL) {
            const jointHandle_t location=CLIPMODEL_ID_TO_JOINT_HANDLE(collision.c.id);
            const bool head=actor->GetHeadEntity()==ent || idStr::Icmp(actor->GetDamageGroup(location),"head")==0;
            if(head) damageDefName=spawnArgs.GetString("def_headshot",damageDefName);
        }
    }
''',f)
 body=replace(body,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_shard")) {
        // A near-instant source shard still leaves a brief optical trace. This
        // visual-only beam uses ordinary entity/removal-event save support.
        const idDeclEntityDef* traceDef=gameLocal.FindEntityDef("reach_needle_contrail",false);
        if(traceDef!=NULL && (collision.endpos-launchOrigin).LengthSqr()>4) {
            idDict args=traceDef->dict;args.SetVector("origin",launchOrigin);
            idEntity* beam=NULL;
            if(gameLocal.SpawnEntityDef(args,&beam,false) && beam!=NULL) {
                renderEntity_t* re=beam->GetRenderEntity();
                re->customShader=declManager->FindMaterial("reach/needle_rifle/contrail");
                re->shaderParms[SHADERPARM_BEAM_END_X]=collision.endpos.x;
                re->shaderParms[SHADERPARM_BEAM_END_Y]=collision.endpos.y;
                re->shaderParms[SHADERPARM_BEAM_END_Z]=collision.endpos.z;
                re->shaderParms[SHADERPARM_BEAM_WIDTH]=.42f;
                re->shaderParms[SHADERPARM_TIMEOFFSET]=-MS2SEC(gameLocal.time);
                re->noShadow=true;re->noSelfShadow=true;
                beam->UpdateVisuals();beam->PostEventMS(&EV_Remove,90);
            }
        }
        idEntity* target=ent;
        if(ent->IsType(idAFAttachment::Type)) target=static_cast<idAFAttachment*>(ent)->GetBody();
        CancelEvents(&EV_Fizzle);CancelEvents(&EV_Explode);
        physicsObj.SetContents(0);physicsObj.SetClipMask(0);
        physicsObj.SetLinearVelocity(vec3_zero);physicsObj.SetAngularVelocity(vec3_zero);physicsObj.SetGravity(vec3_zero);
        physicsObj.SetOrigin(collision.endpos-dir*.35f);
        if(target!=NULL && target->IsType(idActor::Type)) {
            const jointHandle_t joint=CLIPMODEL_ID_TO_JOINT_HANDLE(collision.c.id);
            if(joint!=INVALID_JOINT && ent->GetAnimator()!=NULL) BindToJoint(ent,joint,true);
            else Bind(ent,true);
        } else if(ent!=gameLocal.world) Bind(ent,true);
        spawnArgs.SetBool("_nr_attached",true);spawnArgs.SetInt("_nr_expireAt",gameLocal.time+4000);
        idEntityPtr<idEntity> targetId;targetId=target;spawnArgs.SetInt("_nr_target",targetId.GetSpawnId());
        smokeFly=NULL;smokeFlyTime=0;StartSound("snd_attach",SND_CHANNEL_BODY,0,false,NULL);
        BecomeActive(TH_THINK);physicsObj.PutToRest();
        if(target!=NULL && target->IsType(idActor::Type) && target->health>0) {
            int count=0;
            for(idEntity* e=gameLocal.spawnedEntities.Next();e!=NULL;e=e->spawnNode.Next()) {
                if(!e->IsType(idProjectile::Type)) continue;
                idProjectile* needle=static_cast<idProjectile*>(e);
                if(needle->state==LAUNCHED && needle->owner.GetEntity()==owner.GetEntity() && needle->spawnArgs.GetBool("reach_needle_shard") &&
                   needle->spawnArgs.GetBool("_nr_attached") && needle->spawnArgs.GetInt("_nr_target")==targetId.GetSpawnId() &&
                   needle->spawnArgs.GetInt("_nr_expireAt")>gameLocal.time && needle->spawnArgs.GetInt("_nr_superAt")==0) ++count;
            }
            if(count>=3) {
                for(idEntity* e=gameLocal.spawnedEntities.Next();e!=NULL;e=e->spawnNode.Next()) {
                    if(!e->IsType(idProjectile::Type)) continue;
                    idProjectile* needle=static_cast<idProjectile*>(e);
                    if(needle->state==LAUNCHED && needle->owner.GetEntity()==owner.GetEntity() && needle->spawnArgs.GetBool("reach_needle_shard") &&
                       needle->spawnArgs.GetBool("_nr_attached") && needle->spawnArgs.GetInt("_nr_target")==targetId.GetSpawnId() &&
                       needle->spawnArgs.GetInt("_nr_expireAt")>gameLocal.time && needle->spawnArgs.GetInt("_nr_superAt")==0) {
                        needle->spawnArgs.SetInt("_nr_superAt",gameLocal.time+50);
                        needle->spawnArgs.SetBool("_nr_consumed",needle!=this);
                    }
                }
            }
            if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachNeedle] ATTACH time=%d target=%d count=%d\\n",gameLocal.time,target->entityNumber,count);
        }
        return true;
    }
'''+anchor,f);p=p[:start]+body+p[end:]
 anchor='\t// activate rumble for player\n';p=replace(p,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_needle_shard")) {
        const bool super=spawnArgs.GetBool("_nr_super");
        spawnArgs.Set("def_splash_damage",super ? spawnArgs.GetString("def_super_splash") : "");
        const char* effect=spawnArgs.GetString(super ? "fx_super" : "fx_shatter");
        if(effect[0]) idEntityFx::StartFx(effect,&collision.endpos,&mat3_identity,NULL,false);
        if(!super) spawnArgs.Set("snd_explode",spawnArgs.GetString("snd_shatter"));
        if(lightDefHandle!=-1) {gameRenderWorld->FreeLightDef(lightDefHandle);lightDefHandle=-1;}
        renderLight.lightRadius.Zero();
    }
'''+anchor,f)
 # A bound round must continue processing even while its rigid body rests.
 anchor='if(!common->IsMultiplayer() && (spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket"))) BecomeActive(TH_THINK);'
 assert anchor in p;p=p.replace(anchor,anchor.replace('spawnArgs.GetBool("reach_rocket")','spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_needle_shard")'))
 changed[f]=p
 for f in ['neo/renderer/Image_load.cpp','neo/renderer/RenderBackend.cpp','neo/renderer/Model_prt.cpp']:
  s=changed[f]
  if f.endswith('Image_load.cpp'):
   expr='!idStr::Icmpn(imgName.c_str(),"textures/reach/rocket/fx/",sizeof("textures/reach/rocket/fx/")-1)'
   other=expr.replace('textures/reach/rocket/fx/','textures/reach/needle_rifle/fx/')
  else:
   expr='!idStr::Icmpn('+('shader->GetName()' if f.endswith('RenderBackend.cpp') else 'stage->material->GetName()')+',"reach/rocket/fx/",16)'
   other=expr.replace('reach/rocket/fx/",16','reach/needle_rifle/fx/",22')
  assert expr in s;s=s.replace(expr,'('+expr+' || '+other+')');changed[f]=s
 return changed
