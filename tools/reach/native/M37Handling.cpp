// M37 handling only. Existing spawnargs carry state across saves; no script or
// serialized object layout changes, player speed changes or gameplay RNG calls.
static float ReachM37Setting(const idDict& saved,const idDict& defaults,const char* key,const char* fallback) {
    return saved.GetFloat(key,defaults.GetString(key,fallback));
}
void idWeapon::ReachM37Handling() {
    if(owner==NULL || weaponDef==NULL || common->IsMultiplayer() ||
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")!=0 ||
       !spawnArgs.GetBool("reach_m37_handling",weaponDef->dict.GetString("reach_m37_handling","1"))) {return;}
    SetTimeState clock(timeGroup);
    const int now=gameLocal.time;
    const int previous=spawnArgs.GetInt("_reach_m37HandlingTime","-1");
    const idVec3 relative=owner->GetPhysics()->GetLinearVelocity()-owner->GetPhysics()->GetPushedLinearVelocity();
    const idVec3 gravity=owner->GetPhysics()->GetGravityNormal();
    const float speed=(relative-gravity*(relative*gravity)).Length();
    const float reference=ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_move_reference","140");
    const float target=ReachLMG::Clamp(speed/(reference>1 ? reference : 1),0,1);
    float movement=spawnArgs.GetFloat("_reach_m37Movement","0");
    if(previous<0 || now<previous) {
        movement=target;spawnArgs.SetFloat("_reach_m37Bloom",0);spawnArgs.SetInt("_reach_m37LastShot",-1);
    } else {movement=ReachLMG::Movement(movement,target,float(now-previous)*.001f);}
    spawnArgs.SetFloat("_reach_m37Movement",movement);spawnArgs.SetInt("_reach_m37HandlingTime",now);
    // Old saves restore the weapon's original dictionary, which lacked this key.
    if(spawnArgs.FindKey("reach_sprint_recover_ms")==NULL) {
        spawnArgs.Set("reach_sprint_recover_ms",weaponDef->dict.GetString("reach_sprint_recover_ms","450"));
    }
}
float idWeapon::ReachM37Spread(float original) {
    if(owner==NULL || weaponDef==NULL || common->IsMultiplayer() ||
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")!=0 ||
       !spawnArgs.GetBool("reach_m37_handling",weaponDef->dict.GetString("reach_m37_handling","1"))) {return original;}
    ReachM37Handling();SetTimeState clock(timeGroup);const int now=gameLocal.time;
    const int last=spawnArgs.GetInt("_reach_m37LastShot","-1");
    const int elapsed=last<0 || now<last ? -1 : now-last;
    const float bloom=ReachLMG::Bloom(spawnArgs.GetFloat("_reach_m37Bloom","0"),elapsed,
        int(ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_bloom_hold_ms","140")),
        ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_bloom_recovery",".65"));
    const float movement=spawnArgs.GetFloat("_reach_m37Movement","0");
    const bool crouched=owner->AI_CROUCH;
    const bool grounded=owner->GetPhysics()->HasGroundContacts();
    const float cone=ReachLMG::Spread(bloom,movement,crouched,grounded,
        ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_spread_base",".16"),
        ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_spread_sustained",".46"),
        ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_spread_moving","1.45"),
        ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_spread_airborne","1.8"));
    spawnArgs.SetBool("_reach_m37FirstShot",elapsed<0 || elapsed>180);
    spawnArgs.SetFloat("_reach_m37Bloom",ReachLMG::Clamp(bloom+ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_bloom_per_shot",".045"),0,1));
    spawnArgs.SetInt("_reach_m37LastShot",now);
    if(cvarSystem->GetCVarBool("reach_lmgDebug")) {
        gameLocal.Printf("[ReachLMG] shot t=%d bloom=%.4f move=%.4f crouch=%d ground=%d spread=%.4f\n",now,bloom,movement,int(crouched),int(grounded),cone);
    }
    return cone;
}
void idWeapon::ReachM37Recoil() {
    if(owner==NULL || owner->health<=0 || weaponDef==NULL || common->IsMultiplayer() ||
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")!=0 ||
       !spawnArgs.GetBool("reach_m37_handling",weaponDef->dict.GetString("reach_m37_handling","1"))) {return;}
    const float kick=ReachLMG::AimKick(spawnArgs.GetBool("_reach_m37FirstShot"),owner->AI_CROUCH,
        spawnArgs.GetFloat("_reach_m37Movement","0"),ReachM37Setting(spawnArgs,weaponDef->dict,"reach_m37_aim_recoil_gain","1"));
    idAngles aim=owner->viewAngles;const float before=aim.pitch;
    aim.pitch=idMath::ClampFloat(-89,89,aim.pitch-kick);
    // SetViewAngles updates the host's command-angle delta: mouse compensation
    // works normally and the kick survives the next input update.
    owner->SetViewAngles(aim);
    if(cvarSystem->GetCVarBool("reach_lmgDebug")) {
        gameLocal.Printf("[ReachLMG] recoil before=%.4f after=%.4f kick=%.4f\n",before,aim.pitch,kick);
    }
}
