"""M37 family wiring; no new saved fields or shared-script edits."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';w=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_m37')+' )')
 p=changed['neo/d3xp/Player.cpp'];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0';assert expr in p;changed['neo/d3xp/Player.cpp']=p.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_m37')+' )')
 w=replace(w,'\tassert( modelname );\n','\tassert( modelname );\n    if(!common->IsMultiplayer() && idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0 && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) {modelname="viewmodel_reach_m37_present";}\n',f)
 w=replace(w,'void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{','''void idWeapon::Event_PlayAnim( int channel, const char* animname )
{
    if(!common->IsMultiplayer() && owner!=NULL && channel==ANIMCHANNEL_ALL &&
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0) {
        // Author's v2 graph keyframes, not the AR's magazine timing.
        if(idStr::Cmp(animname,"reload_empty")==0) {spawnArgs.SetFloat("reach_reload_fill_time",spawnArgs.GetFloat("reach_m37_empty_fill","3.3333333"));}
        else if(idStr::Cmp(animname,"reload_full")==0) {spawnArgs.SetFloat("reach_reload_fill_time",spawnArgs.GetFloat("reach_m37_full_fill","2.6666667"));}
        if(idStr::Cmp(animname,"raise")==0 && !owner->spawnArgs.GetBool("_reach_m37Readied")) {
            owner->spawnArgs.SetBool("_reach_m37Readied",true);animname="ready_initial";
        }
    }
''',f)
 # Allow the restored visual recovery tail to finish while idle. Holding fire
 # may still interrupt at the first draft's graph-ready time, after ammo fill.
 w=replace(w,'void idWeapon::Event_AnimDone( int channel, int blendFrames )\n{\n','''void idWeapon::Event_AnimDone( int channel, int blendFrames )
{
    if(!common->IsMultiplayer() && channel==ANIMCHANNEL_ALL && WEAPON_ATTACK &&
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0)
    {
        const idAnimBlend* recovery=animator.CurrentAnim(ANIMCHANNEL_ALL);
        const char* name=recovery!=NULL ? recovery->AnimFullName() : "";
        const bool full=idStr::Cmp(name,"reload_full")==0;
        const bool empty=idStr::Cmp(name,"reload_empty")==0;
        const int ready=full ? 3067 : 3767;
        if((full || empty) && recovery->AnimTime(gameLocal.time)>=ready)
        {idThread::ReturnInt(true);return;}
    }
''',f)
 # Track actual trigger edges separately from script-only attack flags. This
 # resets a short re-press even while the previous fire animation is recovering.
 identity='!common->IsMultiplayer() && idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0'
 w=replace(w,'void idWeapon::BeginAttack()\n{\n','void idWeapon::BeginAttack()\n{\n    if('+identity+') {\n        if(!spawnArgs.GetBool("_reach_m37TriggerDown")) {spawnArgs.SetInt("_reach_m37BurstStart",-1);}\n        spawnArgs.SetBool("_reach_m37TriggerDown",true);\n    }\n',f)
 w=replace(w,'void idWeapon::EndAttack()\n{\n','void idWeapon::EndAttack()\n{\n    if('+identity+' && spawnArgs.GetBool("_reach_m37TriggerDown")) {\n        spawnArgs.SetBool("_reach_m37TriggerDown",false);spawnArgs.SetInt("_reach_m37BurstStart",-1);\n    }\n',f)
 w=replace(w,'void idWeapon::Event_WeaponState( const char* statename, int blendFrames )\n{\n','void idWeapon::Event_WeaponState( const char* statename, int blendFrames )\n{\n    if('+identity+' && idStr::Cmp(statename,"Fire")!=0) {spawnArgs.SetInt("_reach_m37BurstStart",-1);}\n',f)
 # Retain the existing shared script and its serialized layout. Override only
 # its already-declared next_attack float after a successful projectile launch.
 start=w.index('void idWeapon::Event_LaunchProjectiles( ');end=w.index('void idWeapon::Event_LaunchProjectilesEllipse(',start)
 launch=w[start:end]
 anchor='\towner->WeaponFireFeedback( &weaponDef->dict );\n'
 ramp='''    if(!common->IsMultiplayer() && idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0)
    {
        byte* nextAttack=scriptObject.GetVariable("next_attack",ev_float);
        if(nextAttack!=NULL)
        {
            SetTimeState m37BurstClock(timeGroup);
            int started=spawnArgs.GetInt("_reach_m37BurstStart","-1");
            if(started<0 || gameLocal.time<started) {started=gameLocal.time;spawnArgs.SetInt("_reach_m37BurstStart",started);}
            const float fullInterval=spawnArgs.GetFloat("reach_fire_interval",".066");
            const int rampMs=spawnArgs.GetInt("reach_m37_ramp_ms",weaponDef->dict.GetString("reach_m37_ramp_ms","300"));
            const float interval=ReachActions::M37FireInterval(gameLocal.time-started,fullInterval,rampMs);
            *reinterpret_cast<float*>(nextAttack)=float(gameLocal.time)*.001f+interval;
            if(cvarSystem->GetCVarBool("g_debugWeapon")) {gameLocal.Printf("[ReachM37Ramp] t=%d age=%d next=%.6f\\n",gameLocal.time,gameLocal.time-started,interval);}
        }
    }
'''
 launch=replace(launch,anchor,ramp+anchor,f);w=w[:start]+launch+w[end:]
 changed[f]=w;return changed
