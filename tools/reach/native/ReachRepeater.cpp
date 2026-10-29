// Opt-in finite-battery/heat adapter. Existing script bytecode and save layouts
// are retained. Heat/time live in the player's normally saved spawnArgs.
bool idWeapon::ReachRepeaterWeapon() const {
 return !common->IsMultiplayer() && owner!=NULL &&
  idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_plasma_repeater")==0;
}
void idWeapon::ReachRepeaterUpdate() {
 if(!ReachRepeaterWeapon()) {return;}
 const int now=gameLocal.time;const int before=owner->spawnArgs.GetInt("_reach_repeaterTime",va("%d",now));
 float heat=owner->spawnArgs.GetFloat("_reach_repeaterHeat");
 const bool vent=spawnArgs.GetInt("_reach_ventPhase")>0;
 heat=ReachRepeater::Cool(heat,MS2SEC((now>before?now-before:0)),vent,state=="Fire" && WEAPON_ATTACK && !vent);
 owner->spawnArgs.SetFloat("_reach_repeaterHeat",heat);owner->spawnArgs.SetInt("_reach_repeaterTime",now);
 spawnArgs.SetFloat("_reach_heat",heat);spawnArgs.SetFloat("_reach_rate",ReachRepeater::Rate(heat));
 renderEntity.shaderParms[8]=heat;
 if(worldModel.GetEntity()!=NULL) {worldModel.GetEntity()->SetShaderParm(8,heat);}
 ReachRepeaterVisuals();
 // Shared Fire reads this saved script field before setting next_attack.
 idScriptFloat interval;interval.LinkTo(scriptObject,"rate");interval=1.0f/ReachRepeater::Rate(heat);
 if(WEAPON_RELOAD && !vent && heat>.001f && (state=="Idle" || state=="Fire")) {
  idealState="Reload";animBlendFrames=2;
 }
}
void idWeapon::ReachRepeaterVisuals() {
 const int now=gameLocal.time;
 if(spawnArgs.GetInt("_reach_repeaterVisualTime","-1")==now) {return;}
 const int before=spawnArgs.GetInt("_reach_repeaterVisualTime",va("%d",now));
 const float dt=idMath::ClampFloat(0.0f,.1f,MS2SEC(now-before));
 spawnArgs.SetInt("_reach_repeaterVisualTime",now);
 const float heat=owner->spawnArgs.GetFloat("_reach_repeaterHeat");
 const bool vent=spawnArgs.GetInt("_reach_ventPhase")>0;
 const bool energy=owner->inventory.HasAmmo(ammoType,1)>0;
 const bool firing=state=="Fire" && WEAPON_ATTACK && !IsHidden() && !disabled;
 const float oldSpeed=spawnArgs.GetFloat("_reach_repeaterMotorSpeed");
 const float speed=ReachRepeater::ChaseMotor(oldSpeed,ReachRepeater::MotorTarget(heat,firing,vent,energy),dt);
 spawnArgs.SetFloat("_reach_repeaterMotorSpeed",speed);
 const idAnim* source=animator.GetAnim(animator.GetAnim("source_barrel_spin"));
 const jointHandle_t motor=animator.GetJointHandle("b_cylinder");
 if(source!=NULL && source->MD5Anim(0)!=NULL && motor!=INVALID_JOINT) {
  const idMD5Anim* clip=source->MD5Anim(0);
  const float phase=ReachRepeater::MotorPhase(spawnArgs.GetFloat("_reach_repeaterMotorPhase"),oldSpeed,speed,dt,MS2SEC(clip->Length()));
  spawnArgs.SetFloat("_reach_repeaterMotorPhase",phase);
  idJointQuat* pose=(idJointQuat*)_alloca16(clip->NumJoints()*sizeof(idJointQuat));
  const int index=int(motor);frameBlend_t frame;
  clip->ConvertTimeToFrame(int(phase*clip->Length()),0,frame);
  clip->GetInterpolatedFrame(frame,pose,&index,1);
  animator.SetJointAxis(motor,JOINTMOD_LOCAL_OVERRIDE,pose[index].q.ToMat3());
  if(worldModel.GetEntity()!=NULL && worldModel.GetEntity()->GetAnimator()!=NULL) {
   idAnimator* world=worldModel.GetEntity()->GetAnimator();
   const jointHandle_t cylinder=world->GetJointHandle("b_cylinder");
   if(cylinder!=INVALID_JOINT) {world->SetJointAxis(cylinder,JOINTMOD_LOCAL_OVERRIDE,pose[index].q.ToMat3());}
  }
 }
 // The single-frame flaps overlay spreads the rods at the source hot-idle boundary.
 const float autoVent=!vent && !firing ? idMath::ClampFloat(0.0f,1.0f,(heat-.97f)/.03f) : 0.0f;
 const jointHandle_t left=animator.GetJointHandle("b_rod_left");
 const jointHandle_t right=animator.GetJointHandle("b_rod_right");
 animator.SetJointPos(left,JOINTMOD_LOCAL,idVec3(0,1.2f*autoVent,0));
 animator.SetJointPos(right,JOINTMOD_LOCAL,idVec3(0,-1.2f*autoVent,0));
 renderEntity.shaderParms[9]=vent?1.0f:autoVent;
 renderEntity.shaderParms[10]=energy?1.0f:0.0f;
 // The shared AR counter owns parms 9/10. Slot 7 is unused by the shared armor.
 renderEntity.shaderParms[7]=energy?1.0f:0.0f;
 if(worldModel.GetEntity()!=NULL) {
  worldModel.GetEntity()->SetShaderParm(9,renderEntity.shaderParms[9]);
  worldModel.GetEntity()->SetShaderParm(10,renderEntity.shaderParms[10]);
  worldModel.GetEntity()->SetShaderParm(7,renderEntity.shaderParms[7]);
 }
 // Tag every registered Repeater emitter with the same FP view/projection scope.
 for(int i=0;i<weaponParticles.Num();++i) {
  WeaponParticle_t* part=weaponParticles.GetIndex(i);
  if(part->emitter==NULL || part->smoke) {continue;}
  renderEntity_t* re=part->emitter->GetRenderEntity();
  re->allowSurfaceInViewID=owner->entityNumber+1;re->weaponDepthHack=true;
  re->noShadow=true;re->noOverlays=true;re->shaderParms[6]=1.0f;
  re->shaderParms[8]=heat;re->shaderParms[9]=renderEntity.shaderParms[9];re->shaderParms[10]=renderEntity.shaderParms[10];
  re->shaderParms[7]=renderEntity.shaderParms[7];
  part->emitter->spawnArgs.SetBool("cycleTrigger",true);
 }
 const bool motorLive=spawnArgs.GetBool("_reach_repeaterMotorSound");
 if(speed>.02f && !motorLive) {StartSound("snd_reach_motor",SND_CHANNEL_BODY2,0,false,NULL);spawnArgs.SetBool("_reach_repeaterMotorSound",true);}
 else if(speed<=.02f && motorLive) {StopSound(SND_CHANNEL_BODY2,false);spawnArgs.SetBool("_reach_repeaterMotorSound",false);}
 const bool arcLive=spawnArgs.GetBool("_reach_repeaterArcSound");
 if(vent && energy && !arcLive) {StartSound("snd_reach_arc",SND_CHANNEL_BODY3,0,false,NULL);Event_StartWeaponParticle("reach_repeater_arc");spawnArgs.SetBool("_reach_repeaterArcSound",true);}
 else if((!vent || !energy) && arcLive) {StopSound(SND_CHANNEL_BODY3,false);Event_StopWeaponParticle("reach_repeater_arc");spawnArgs.SetBool("_reach_repeaterArcSound",false);}
 if(cvarSystem->GetCVarBool("g_debugWeapon") && now-spawnArgs.GetInt("_reach_repeaterVisualDebug")>=100) {
  spawnArgs.SetInt("_reach_repeaterVisualDebug",now);
  gameLocal.Printf("[ReachRepeaterVisual] t=%d speed=%.5f phase=%.5f vent=%d auto=%.5f energy=%d\n",now,speed,spawnArgs.GetFloat("_reach_repeaterMotorPhase"),vent?1:0,autoVent,energy?1:0);
 }
}
bool idWeapon::ReachRepeaterShot() {
 if(!ReachRepeaterWeapon()) {return true;}
 ReachRepeaterUpdate();
 if(spawnArgs.GetInt("_reach_ventPhase")!=0 || owner->inventory.HasAmmo(ammoType,ammoRequired)==0) {return false;}
 const int now=gameLocal.time;const int due=spawnArgs.GetInt("_reach_repeaterNextShot");
 if(now<due) {return false;}
 const float before=owner->spawnArgs.GetFloat("_reach_repeaterHeat");
 const float after=ReachRepeater::Shot(before);
 owner->spawnArgs.SetFloat("_reach_repeaterHeat",after);owner->spawnArgs.SetInt("_reach_repeaterTime",now);
 spawnArgs.SetFloat("_reach_heat",after);spawnArgs.SetInt("_reach_repeaterNextShot",now+int(1000.0f/ReachRepeater::Rate(before)+.5f));
 if(cvarSystem->GetCVarBool("g_debugWeapon")) {gameLocal.Printf("[ReachRepeater] SHOT time=%d heat=%.5f rate=%.5f batteryBefore=%d\n",now,after,ReachRepeater::Rate(before),owner->inventory.HasAmmo(ammoType,1));}
 return true;
}
bool idWeapon::ReachRepeaterAnimDone(int channel) {
 if(!ReachRepeaterWeapon() || channel!=ANIMCHANNEL_ALL || spawnArgs.GetInt("_reach_ventPhase")==0) {return false;}
 ReachRepeaterUpdate();
 int phase=spawnArgs.GetInt("_reach_ventPhase");
 const int exitAnim=animator.GetAnim("vent_exit");
 const float exitSeconds=exitAnim!=0?MS2SEC(animator.AnimLength(exitAnim)):0;
 const bool exiting=owner->spawnArgs.GetFloat("_reach_repeaterHeat")<=exitSeconds/2.5f+.001f;
 // The source loop can leave at the cooling boundary; do not add a whole
 // loop merely because the threshold falls between two loop endpoints.
 if(gameLocal.time<animDoneTime && !(phase==2 && exiting)) {idThread::ReturnInt(false);return true;}
 if(phase==3) {
  spawnArgs.SetInt("_reach_ventPhase",0);
  Event_StopWeaponParticle("reach_vent1");Event_StopWeaponParticle("reach_vent2");
  if(cvarSystem->GetCVarBool("g_debugWeapon")) {gameLocal.Printf("[ReachRepeater] VENT_END heat=%.5f battery=%d\n",owner->spawnArgs.GetFloat("_reach_repeaterHeat"),owner->inventory.HasAmmo(ammoType,1));}
  idThread::ReturnInt(true);return true;
 }
 // Finish cooling during the source exit clip; do not touch battery inventory.
 const char* next=exiting?"vent_exit":"vent_loop";
 const int anim=animator.GetAnim(next);if(anim==0) {gameLocal.Error("Repeater missing %s",next);}
 animator.PlayAnim(channel,anim,gameLocal.time,FRAME2MS(1));animDoneTime=animator.CurrentAnim(channel)->GetEndTime();
 spawnArgs.SetInt("_reach_ventPhase",exiting?3:2);idThread::ReturnInt(false);return true;
}
