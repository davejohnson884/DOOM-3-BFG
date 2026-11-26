"""Fuel Rod BFG replacement; opt-in only, existing script/save interfaces."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';s=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
  assert expr in s;s=s.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_fuelrod')+' )')
 anchor='\tassert( modelname );\n'
 s=replace(s,anchor,anchor+'    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod") && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) modelname="viewmodel_reach_fuelrod_present";\n',f)
 anchor='void idWeapon::PresentWeapon( bool showViewModel )\n{\n'
 s=replace(s,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && weaponDef!=NULL &&
       idStr::Cmp(weaponDef->GetName(),"weapon_bfg")==0 && weaponDef->dict.GetBool("reach_fuelrod") &&
       !spawnArgs.GetBool("reach_fuelrod")) {
        const int loaded=ammoClip.Get();GetWeaponDef("weapon_bfg",loaded);
        gameLocal.Printf("[ReachFuelRod] legacy BFG migrated; clip=%d reserve=%d\\n",ammoClip.Get(),owner->inventory.GetInventoryAmmoForType(ammoType));
    }
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod")) {
        if(weaponDef!=NULL) spawnArgs.SetFloat("reach_weapon_fov",weaponDef->dict.GetFloat("reach_weapon_fov","60"));
        renderEntity.shaderParms[11]=spawnArgs.GetFloat("reach_weapon_fov","60");
        if(owner!=NULL && owner->health>0 && !gameLocal.inCinematic) {
            const bool zoomDown=(owner->usercmd.buttons&BUTTON_ZOOM)!=0;
            if(zoomDown!=spawnArgs.GetBool("_fuel_zoomDown")) {
                StartSound(zoomDown ? "snd_reach_zoom_in" : "snd_reach_zoom_out",SND_CHANNEL_ITEM,0,false,NULL);
                spawnArgs.SetBool("_fuel_zoomDown",zoomDown);
            }
        }
        const idAnimBlend* a=animator.CurrentAnim(ANIMCHANNEL_ALL);
        const bool reload=a!=NULL && strstr(a->AnimFullName(),"reload")!=NULL;
        const float age=reload ? a->AnimTime(gameLocal.time)/1000.0f : 0;
        renderEntity.shaderParms[7]=reload ? idMath::ClampFloat(0,1,(age-.7f)*5)*idMath::ClampFloat(0,1,(2.55f-age)*5) : 0;
        renderEntity.shaderParms[8]=idMath::ClampFloat(0,1,float(ammoClip.Get())/5.0f);
        if(worldModel.GetEntity()!=NULL) {
            worldModel.GetEntity()->GetRenderEntity()->shaderParms[7]=renderEntity.shaderParms[7];
            worldModel.GetEntity()->GetRenderEntity()->shaderParms[8]=renderEntity.shaderParms[8];worldModel.GetEntity()->UpdateVisuals();
        }
        if(owner!=NULL && idStr::Cmp(state.c_str(),"Idle")==0 && ammoClip.Get()==0 &&
           owner->inventory.HasAmmo(ammoType,ammoRequired)>0 &&
           session->GetActingGameStateLobbyBase().GetLobbyUserWeaponAutoReload(gameLocal.lobbyUserIDs[owner->entityNumber])) WEAPON_RELOAD=true;
    }
''',f)
 anchor='void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{\n'
 s=replace(s,anchor,anchor+'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod") && channel==ANIMCHANNEL_ALL) {
        if(strstr(animname,"reload")!=NULL) spawnArgs.SetFloat("reach_reload_fill_time",43.0f/30.0f);
        if(idStr::Cmp(animname,"fire")==0) {
            const int variant=spawnArgs.GetInt("_fuel_fireVariant")%3+1;spawnArgs.SetInt("_fuel_fireVariant",variant);
            animname=variant==1 ? "fire_a" : variant==2 ? "fire_b" : "fire_c";
        }
        if(idStr::Cmp(animname,"melee")==0) animname=spawnArgs.GetInt("_fuel_meleeVariant")==2 ? "melee2" : "melee1";
    }
''',f)
 anchor='\tidThread::ReturnFloat( action );\n'
 s=replace(s,anchor,'''    if(action==1 && spawnArgs.GetBool("reach_fuelrod")) {
        const int variant=spawnArgs.GetInt("_fuel_meleeVariant")==1 ? 2 : 1;
        spawnArgs.SetInt("_fuel_meleeVariant",variant);spawnArgs.SetInt("reach_melee_recover_ms",variant==1 ? 1400 : 1033);
    }
'''+anchor,f)
 anchor='int\tidWeapon::GetZoomFov()\n{\n'
 s=replace(s,anchor,anchor+'''    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_fuelrod"))
        return idMath::Ftoi(RAD2DEG(2*idMath::ATan(idMath::Tan(DEG2RAD(owner->DefaultFov()*.5f))/2.0f)));
''',f)
 anchor='void idWeapon::Event_AnimDone( int channel, int blendFrames )\n{\n'
 s=replace(s,anchor,anchor+'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod") && channel==ANIMCHANNEL_ALL && WEAPON_ATTACK) {
        const idAnimBlend* a=animator.CurrentAnim(channel);
        // The source ready-for-use event is frame80; retain the complete
        // 90-frame visual recovery when the player has not requested fire.
        if(a!=NULL && strstr(a->AnimFullName(),"reload")!=NULL && a->AnimTime(gameLocal.time)>=2667)
            {idThread::ReturnInt(true);return;}
    }
''',f)
 s=s.replace('const bool authored=needle ||','const bool fuelrod=spawnArgs.GetBool("reach_fuelrod");\n    const bool authored=fuelrod || needle ||')
 s=s.replace('if(needle || shotgunAction ||','if(fuelrod || needle || shotgunAction ||')
 s=s.replace('shotgun || m37Source || rocket);','shotgun || m37Source || rocket || fuelrod);')
 changed[f]=s
 # Source-authored weapon FOV must also govern the attached flash and projected
 # world-smoke origins; keep every other weapon's fallback exactly as before.
 s=changed[f]
 for expr in ['spawnArgs.GetBool("reach_needle_rifle") ? spawnArgs.GetFloat("reach_weapon_fov","68")', 'if(spawnArgs.GetBool("reach_needle_rifle")) flash->shaderParms[11]=spawnArgs.GetFloat("reach_weapon_fov","68");']:
  assert expr in s,expr
  if expr.startswith('if('):new=expr.replace('spawnArgs.GetBool("reach_needle_rifle")','(spawnArgs.GetBool("reach_needle_rifle") || spawnArgs.GetBool("reach_fuelrod"))').replace('"68"','spawnArgs.GetBool("reach_fuelrod") ? "60" : "68"')
  else:new=expr.replace('spawnArgs.GetBool("reach_needle_rifle")','(spawnArgs.GetBool("reach_needle_rifle") || spawnArgs.GetBool("reach_fuelrod"))').replace('"68"','spawnArgs.GetBool("reach_fuelrod") ? "60" : "68"')
  s=s.replace(expr,new)
 changed[f]=s
 f='neo/d3xp/Player.cpp';s=changed[f];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_m319" ) == 0'
 assert expr in s;changed[f]=s.replace(expr,'( '+expr+' || '+expr.replace('reach_m319','reach_fuelrod')+' )')
 f='neo/d3xp/Projectile.cpp';s=changed[f]
 s=replace(s,'#include "ReachM319Policy.h"','#include "ReachM319Policy.h"\n#include "ReachFuelRodPolicy.h"',f)
 anchor='\tlaunchOrigin = start;\n'
 s=replace(s,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod")) {
        spawnArgs.SetVector("_fuel_previous",start);spawnArgs.SetFloat("_fuel_distance",0);
    }
'''+anchor,f)
 anchor='void idProjectile::Think()\n{\n'
 s=replace(s,anchor,anchor+'''    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_fuelrod")) {
        const idVec3 position=physicsObj.GetOrigin();
        const float distance=spawnArgs.GetFloat("_fuel_distance")+(position-spawnArgs.GetVector("_fuel_previous")).Length();
        spawnArgs.SetFloat("_fuel_distance",distance);spawnArgs.SetVector("_fuel_previous",position);
        idVec3 direction=physicsObj.GetLinearVelocity();
        if(direction.Normalize()>0) {
            const float speed=ReachFuelRod::Speed(distance);physicsObj.SetLinearVelocity(direction*speed);
            idMat3 axis=direction.ToAngles().ToMat3();const idVec3 forward=axis[0];axis[0]=-axis[2];axis[2]=forward;physicsObj.SetAxis(axis);
            if(cvarSystem->GetCVarBool("g_debugWeapon") && gameLocal.time>=spawnArgs.GetInt("_fuel_nextTrace")) {
                gameLocal.Printf("[FUELFLIGHT] time=%d distance=%.2f speed=%.2f\\n",gameLocal.time,distance,speed);spawnArgs.SetInt("_fuel_nextTrace",gameLocal.time+100);
            }
        }
        if(distance>=spawnArgs.GetFloat("reach_fuel_range","9600")) PostEventMS(&EV_Explode,0);
    }
''',f)
 anchor='\t// direction of projectile\n\tdir = velocity;\n'
 s=replace(s,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_fuelrod")) {
        idVec3 incoming=velocity;const float speed=incoming.Normalize();
        const bool actor=ent->IsType(idActor::Type) || ent->IsType(idAFAttachment::Type);
        const float incidence=-incoming*collision.c.normal;
        const bool bounce=ReachFuelRod::Bounce(actor,speed,incidence);
        projectileFlags.detonate_on_world=!bounce;projectileFlags.detonate_on_actor=true;
        if(bounce) {
            physicsObj.SetLinearVelocity(velocity-2.0f*(velocity*collision.c.normal)*collision.c.normal);
            physicsObj.SetAngularVelocity(vec3_zero);physicsObj.SetOrigin(collision.endpos+.4f*collision.c.normal);
        }
        if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[FUELCONTACT] time=%d actor=%d bounce=%d speed=%.2f incidence=%.4f\\n",gameLocal.time,actor ? 1 : 0,bounce ? 1 : 0,speed,incidence);
    }
'''+anchor,f)
 # Only extend the existing opt-in lifecycle/effect/light hooks. The rocket
 # acceleration and tube controller remain rocket-only.
 s=s.replace('(spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket"))) BecomeActive','(spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_fuelrod"))) BecomeActive')
 s=s.replace('spawnArgs.GetBool("reach_frag_ballistics"))) BecomeActive','spawnArgs.GetBool("reach_frag_ballistics") || spawnArgs.GetBool("reach_fuelrod"))) BecomeActive')
 s=s.replace('if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket")) {\n        renderLight.lightId','if(!common->IsMultiplayer() && (spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_fuelrod"))) {\n        renderLight.lightId')
 s=s.replace('const bool reachRocketLight=!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket");','const bool reachRocketLight=!common->IsMultiplayer() && (spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_fuelrod"));')
 s=s.replace('if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket")) {\n        if(lightDefHandle','if(!common->IsMultiplayer() && (spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_fuelrod"))) {\n        if(lightDefHandle')
 s=s.replace('spawnArgs.GetBool("reach_frag_fx"))) {','spawnArgs.GetBool("reach_frag_fx") || spawnArgs.GetBool("reach_fuelrod"))) {')
 s=s.replace('(spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_m319") ||\n        idStr::Cmp(GetEntityDefName()', '(spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_fuelrod") ||\n        idStr::Cmp(GetEntityDefName()')
 changed[f]=s
 for f in ['neo/renderer/Image_load.cpp','neo/renderer/RenderBackend.cpp','neo/renderer/Model_prt.cpp']:
  s=changed[f]
  if f.endswith('Image_load.cpp'):
   expr='!idStr::Icmpn(imgName.c_str(),"textures/reach/rocket/fx/",sizeof("textures/reach/rocket/fx/")-1)';new=expr.replace('rocket','fuelrod')
  else:
   expr='!idStr::Icmpn('+('shader->GetName()' if f.endswith('RenderBackend.cpp') else 'stage->material->GetName()')+',"reach/rocket/fx/",16)';new=expr.replace('reach/rocket/fx/",16','reach/fuelrod/fx/",17')
  assert expr in s;s=s.replace(expr,'('+expr+' || '+new+')');changed[f]=s
 # Extend only the Fuel Rod launch and Think branches.
 from pathlib import Path
 f='neo/d3xp/Projectile.cpp';s=changed[f]
 anchor='spawnArgs.SetVector("_fuel_previous",start);spawnArgs.SetFloat("_fuel_distance",0);'
 s=replace(s,anchor,anchor+'\n        spawnArgs.SetInt("_fuel_launchTime",gameLocal.time);spawnArgs.SetBool("_fuel_ignited",false);\n        spawnArgs.Set("smoke_fly",spawnArgs.GetString("smoke_fly_arming","reach_fuelrod_arming.prt"));',f)
 anchor='if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_fuelrod")) {\n'
 s=replace(s,anchor,anchor+(Path(__file__).resolve().parent/'FuelRodFlight.cpp').read_text()+'\n',f)
 changed[f]=s
 return changed
