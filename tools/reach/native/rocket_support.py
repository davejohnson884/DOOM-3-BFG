"""Reach twin-tube launcher. Uses existing archive fields and shared script ABI."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';w=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_rocket')+' )')
 fplayer='neo/d3xp/Player.cpp';p=changed[fplayer]
 expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
 assert expr in p;changed[fplayer]=p.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_rocket')+' )')
 w=replace(w,'\tassert( modelname );\n','\tassert( modelname );\n    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket") && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) modelname="viewmodel_reach_rocket_present";\n',f)
 w=replace(w,'\tammoClip = ammoinclip;\n','''    // Legacy inventory clips may hold five. Return only the excess to the
    // separate reserve before adopting the two-tube capacity. No free rounds.
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket") && ammoinclip>clipSize) {
        const int reserve=owner->inventory.GetInventoryAmmoForType(ammoType);
        if(reserve>=0) owner->inventory.SetInventoryAmmoForType(ammoType,reserve+ammoinclip-clipSize);
        ammoinclip=clipSize;
    }
\tammoClip = ammoinclip;
''',f)
 w=replace(w,'void idWeapon::PresentWeapon( bool showViewModel )\n{\n','''void idWeapon::PresentWeapon( bool showViewModel )
{
    if(!common->IsMultiplayer() && owner!=NULL && weaponDef!=NULL &&
       idStr::Cmp(weaponDef->GetName(),"weapon_rocketlauncher")==0 && weaponDef->dict.GetBool("reach_rocket") &&
       idStr::Cmp(scriptObject.GetTypeName(),"weapon_rocketlauncher")==0) {
        const int loaded=ammoClip.Get();GetWeaponDef("weapon_rocketlauncher",loaded);
        gameLocal.Printf("[ReachRocket] legacy launcher migrated; loaded=%d reserve=%d\\n",ammoClip.Get(),owner->inventory.HasAmmo(ammoType,1));
    }
''',f)
 for method in ['PlayAnim','PlayCycle']:
  anchor='void idWeapon::Event_'+method+'( int channel, const char* animname )\n{\n'
  code='''    idStr rocketAnimation;
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket") && channel==ANIMCHANNEL_ALL) {
        const bool fire=idStr::Cmp(animname,"fire")==0;
        if(fire) {
            rocketAnimation=ammoClip.Get()==1 ? "fire_a" : "fire_b";
            const char* effect=spawnArgs.GetString("smoke_reach_backwash");
            const jointHandle_t joint=animator.GetJointHandle("backwash");
            if(effect[0] && joint!=INVALID_JOINT && gameLocal.isNewFrame) {
                idVec3 origin;idMat3 axis;GetGlobalJointTransform(true,joint,origin,axis);
                const renderView_t* view=owner!=NULL ? owner->GetRenderView() : NULL;
                if(view!=NULL) {
                    const float scale=ReachMuzzle::WorldSmokeScale(cvarSystem->GetCVarFloat("r_reachWeaponFov"),view->fov_y);
                    const idVec3 delta=origin-playerViewOrigin;
                    origin=playerViewOrigin+(delta*playerViewAxis[0])*playerViewAxis[0]+
                        scale*((delta*playerViewAxis[1])*playerViewAxis[1]+(delta*playerViewAxis[2])*playerViewAxis[2]);
                }
                axis[0]=-axis[0];axis[2]=-axis[2];
                const idDeclParticle* particle=static_cast<const idDeclParticle*>(declManager->FindType(DECL_PARTICLE,effect));
                gameLocal.smokeParticles->EmitSmoke(particle,gameLocal.time,gameLocal.random.RandomFloat(),origin,axis,timeGroup);
            }
        }
        else {
            rocketAnimation=idStr::Cmp(animname,"melee")==0 ?
                (spawnArgs.GetInt("_rocket_meleeVariant")==2 ? "melee2" : "melee1") : animname;
            if(ammoClip.Get()==1) rocketAnimation+="_half";
        }
        if(animator.GetAnim(rocketAnimation.c_str())!=0) animname=rocketAnimation.c_str();
        if(strstr(animname,"reload")!=NULL) spawnArgs.SetFloat("reach_reload_fill_time",80.0f/30);
        if(cvarSystem->GetCVarBool("g_debugWeapon"))
            gameLocal.Printf("[ReachRocket] anim=%s loaded=%d time=%d\\n",animname,ammoClip.Get(),gameLocal.time);
    }
'''
  w=replace(w,anchor,anchor+code,f)
 w=replace(w,'void idWeapon::Event_ReachQuickAction()\n{\n','''void idWeapon::Event_ReachQuickAction()
{
''',f)
 anchor='\tidThread::ReturnFloat( action );\n'
 w=replace(w,anchor,'''    if(action==1 && spawnArgs.GetBool("reach_rocket")) {
        const int variant=spawnArgs.GetInt("_rocket_meleeVariant")==1 ? 2 : 1;
        spawnArgs.SetInt("_rocket_meleeVariant",variant);
        // Quick computes its recovery deadline before requesting the clip.
        spawnArgs.SetInt("reach_melee_recover_ms",variant==1 ? 1366 : 866);
    }
'''+anchor,f)
 anchor='void idWeapon::Event_AnimDone( int channel, int blendFrames )\n{\n'
 w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket") && channel==ANIMCHANNEL_ALL && WEAPON_ATTACK) {
        const idAnimBlend* a=animator.CurrentAnim(channel);
        if(a!=NULL && strstr(a->AnimFullName(),"reload")!=NULL && a->AnimTime(gameLocal.time)>=3334)
            {idThread::ReturnInt(true);return;}
    }
''',f)
 anchor='int\tidWeapon::GetZoomFov()\n{\n'
 w=replace(w,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_rocket"))
        return idMath::Ftoi(RAD2DEG(2*idMath::ATan(idMath::Tan(DEG2RAD(owner->DefaultFov()*.5f))/1.8f)));
''',f)
 changed[f]=w
 f='neo/d3xp/Projectile.cpp';p=changed[f]
 anchor='void idProjectile::Think()\n{\n'
 p=replace(p,anchor,anchor+'''    // Source acceleration is specified over distance, not a timed thrust.
    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_rocket")) {
        const idVec3 position=physicsObj.GetOrigin();
        const float distance=spawnArgs.GetFloat("_rocket_distance")+(position-spawnArgs.GetVector("_rocket_previous")).Length();
        spawnArgs.SetFloat("_rocket_distance",distance);spawnArgs.SetVector("_rocket_previous",position);
        idVec3 direction=physicsObj.GetLinearVelocity();
        if(direction.Normalize()>0) {
            const float speed=960+960*idMath::ClampFloat(0,1,distance/3600);
            physicsObj.SetLinearVelocity(direction*speed);
            idAngles angles=direction.ToAngles();idMat3 axis=angles.ToMat3();
            // idProjectile local Z is forward. Keep the rocket nose and
            // exhaust aligned to its actual flight vector, including gravity.
            const idVec3 forward=axis[0];axis[0]=-axis[2];axis[2]=forward;
            physicsObj.SetAxis(axis);
        }
        if(distance>=21000) {PostEventMS(&EV_Explode,0);}
    }
''',f)
 anchor='\tlaunchOrigin = start;\n'
 p=replace(p,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket")) {
        spawnArgs.SetVector("_rocket_previous",start);spawnArgs.SetFloat("_rocket_distance",0);
    }
'''+anchor,f)
 # Both launch and restore must keep the source acceleration controller awake.
 p=p.replace('spawnArgs.GetBool("reach_m319")) BecomeActive(TH_THINK);','(spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket"))) BecomeActive(TH_THINK);')
 # Opt in only to the visual composition hook, not the M319 latch controller.
 anchor='if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) {\n        const char* visualFx='
 assert p.count(anchor)==1;p=p.replace(anchor,anchor.replace('spawnArgs.GetBool("reach_m319")','(spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket"))'))
 changed[f]=p
 # Reuse the established soft-particle material ABI for the rocket namespace.
 for f in ['neo/renderer/Image_load.cpp','neo/renderer/RenderBackend.cpp','neo/renderer/Model_prt.cpp']:
  s=changed[f]
  if f.endswith('Image_load.cpp'):
   expr='!idStr::Icmpn(imgName.c_str(),"textures/reach/m319/fx/r6/",sizeof("textures/reach/m319/fx/r6/")-1)'
   replacement='('+expr+' || !idStr::Icmpn(imgName.c_str(),"textures/reach/rocket/fx/",sizeof("textures/reach/rocket/fx/")-1))'
  else:
   expr='!idStr::Icmpn('+('shader->GetName()' if f.endswith('RenderBackend.cpp') else 'stage->material->GetName()')+',"reach/m319/r6/",14)'
   replacement='('+expr+' || '+expr.replace('reach/m319/r6/",14','reach/rocket/fx/",16')+')'
  assert expr in s;s=s.replace(expr,replacement);changed[f]=s
 return changed
