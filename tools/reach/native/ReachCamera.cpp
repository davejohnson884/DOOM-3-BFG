// Reach opt-in weapon projection / animation camera. No asset or save changes.
// Non-archived presentation controls: tuning does not rewrite user settings.
static idCVar reach_cameraFireScale("reach_cameraFireScale","2.2",CVAR_GAME|CVAR_FLOAT,
    "Reach AR firing camera strength relative to the original camera pass",0.0f,4.0f);
static idCVar reach_cameraReloadScale("reach_cameraReloadScale","2.5",CVAR_GAME|CVAR_FLOAT,
    "Reach AR reload camera strength relative to the original camera pass",0.0f,4.0f);
static idCVar reach_cameraSprintScale("reach_cameraSprintScale","2.8",CVAR_GAME|CVAR_FLOAT,
    "Reach AR sprint camera strength relative to the original camera pass",0.0f,4.0f);
static idCVar reach_cameraMeleeScale("reach_cameraMeleeScale","2.8",CVAR_GAME|CVAR_FLOAT,
    "Reach AR melee camera strength relative to the original camera pass",0.0f,4.0f);
static idCVar reach_cameraThrowScale("reach_cameraThrowScale","1",CVAR_GAME|CVAR_FLOAT,
    "Reach AR grenade throw camera strength",0.0f,4.0f);

static idCVar reach_cameraWalkScale("reach_cameraWalkScale","1",CVAR_GAME|CVAR_FLOAT,
    "Reach AR walking camera strength",0.0f,4.0f);

bool idWeapon::ReachCameraMotion( idVec3& offset, idAngles& angles )
{
    offset.Zero();angles.Zero();
    if( owner==NULL || owner->health<=0 || common->IsMultiplayer() ||
        !ReachCombatWeapon(spawnArgs) || !spawnArgs.GetBool("reach_authored_motion") ||
        !spawnArgs.GetBool("reach_camera_motion","1") )
    {
        reachCamera.Reset();return false;
    }
    // Compass consumes its own unused shader parameter, separate from ammo.
    renderEntity.shaderParms[11]=ReachCamera::CompassTurns(owner->viewAngles.yaw-
        spawnArgs.GetFloat("reach_compass_north","0"));
    SetTimeState cameraClock(timeGroup);
    const int now=gameLocal.time;
    const idAnimBlend* blend=animator.CurrentAnim(ANIMCHANNEL_ALL);
    const char* name=blend!=NULL ? blend->AnimFullName() : "";
    const float phase=blend!=NULL && blend->Length()>0 ?
        ReachCamera::Limit(float(blend->AnimTime(now))/float(blend->Length()),0,1) : 0;
    const bool sprintLoop=strstr(name,"sprint_loop")!=NULL && strstr(name,"airborne")==NULL;
    const bool melee=strstr(name,"melee")!=NULL;
    const bool authored=sprintLoop || melee || strstr(name,"throw_grenade")!=NULL;
    ReachCamera::Profile profile=ReachCamera::None;
    if( strstr(name,"reload_empty")!=NULL ) {profile=ReachCamera::ReloadEmpty;}
    else if( strstr(name,"reload")!=NULL ) {profile=ReachCamera::Reload;}
    else if( strstr(name,"throw_grenade")!=NULL ) {profile=ReachCamera::Throw;}
    else if( strstr(name,"sprint_enter")!=NULL ) {profile=ReachCamera::SprintEnter;}
    else if( strstr(name,"sprint_exit")!=NULL ) {profile=ReachCamera::SprintExit;}
    else if( sprintLoop ) {profile=ReachCamera::SprintLoop;}
    else if( strstr(name,"raise")!=NULL || strstr(name,"ready")!=NULL ) {profile=ReachCamera::Raise;}
    else if( strstr(name,"putaway")!=NULL || strstr(name,"put_away")!=NULL ) {profile=ReachCamera::Lower;}
    float gain=1;
    if( melee ) {gain=reach_cameraMeleeScale.GetFloat();}
    else if( profile==ReachCamera::Throw ) {gain=reach_cameraThrowScale.GetFloat();}
    else if( profile==ReachCamera::Reload || profile==ReachCamera::ReloadEmpty ) {gain=reach_cameraReloadScale.GetFloat();}
    else if( profile==ReachCamera::SprintEnter || profile==ReachCamera::SprintLoop || profile==ReachCamera::SprintExit ) {gain=reach_cameraSprintScale.GetFloat();}
    // All accepted gains remain unchanged; only the throw gets its new profile.
    ReachCamera::Motion target=ReachCamera::ScaleMotion(ReachCamera::ProfileMotion(profile,phase),gain);
    if( authored )
    {
        idVec3 cameraOrigin;idMat3 cameraAxis;
        const jointHandle_t joint=animator.GetJointHandle("camera_control");
        // Parent-local space cancels the accepted root pose and weapon anchor.
        // GetJointLocalTransform evaluates the original animation blend at now.
        if( animator.GetJointLocalTransform(joint,now,cameraOrigin,cameraAxis) )
        {
            const idAngles cameraAngles=cameraAxis.ToAngles();
            for( int i=0;i<3;++i )
            {
                target.p[i]+=cameraOrigin[i]*.55f*gain;
                target.a[i]+=idMath::AngleNormalize180(cameraAngles[i])*.65f*gain;
            }
        }
    }
    const bool locomotion=profile==ReachCamera::None && !melee &&
        (strstr(name,"source_moving")!=NULL || strstr(name,"idle")!=NULL || strstr(name,"fire")!=NULL);
    const idVec3 relativeVelocity=owner->GetPhysics()->GetLinearVelocity()-owner->GetPhysics()->GetPushedLinearVelocity();
    const idVec3 gravityDirection=owner->GetPhysics()->GetGravityNormal();
    const float walkingSpeed=(relativeVelocity-gravityDirection*(relativeVelocity*gravityDirection)).Length();
    const bool walking=locomotion && owner->GetPhysics()->HasGroundContacts() &&
        (owner->usercmd.forwardmove!=0 || owner->usercmd.rightmove!=0) && walkingSpeed>5;
    const ReachCamera::Motion stride=ReachCamera::ScaleMotion(reachCamera.Walk(now,walkingSpeed,walking),reach_cameraWalkScale.GetFloat());
    for(int i=0;i<3;++i) {target.p[i]+=stride.p[i];target.a[i]+=stride.a[i];}
    const ReachCamera::Motion motion=reachCamera.Evaluate(now,target,reach_cameraFireScale.GetFloat());
    for( int i=0;i<3;++i ) {offset[i]=motion.p[i];angles[i]=motion.a[i];}
    if( cvarSystem->GetCVarBool("reach_cameraDebug") && reachCamera.debugTime!=now )
    {
        reachCamera.debugTime=now;
        gameLocal.Printf("[ReachCamera] t=%d anim=%s phase=%.4f pos=%.5f,%.5f,%.5f ang=%.5f,%.5f,%.5f shots=%d\n",
            now,name,phase,offset.x,offset.y,offset.z,angles.pitch,angles.yaw,angles.roll,reachCamera.sequence);
    }
    return true;
}
