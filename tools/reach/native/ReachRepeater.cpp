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
 // Shared Fire reads this saved script field before setting next_attack.
 idScriptFloat interval;interval.LinkTo(scriptObject,"rate");interval=1.0f/ReachRepeater::Rate(heat);
 if(WEAPON_RELOAD && !vent && heat>.001f && (state=="Idle" || state=="Fire")) {
  idealState="Reload";animBlendFrames=2;
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
