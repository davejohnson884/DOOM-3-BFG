// Reach opt-in weapon projection / animation camera. No asset or save changes.
bool idWeapon::ReachCameraMotion( idVec3& offset, idAngles& angles )
{
    offset.Zero();angles.Zero();
    if( owner==NULL || owner->health<=0 || common->IsMultiplayer() ||
        !ReachCombatWeapon(spawnArgs) || !spawnArgs.GetBool("reach_authored_motion") ||
        !spawnArgs.GetBool("reach_camera_motion","1") )
    {
        reachCamera.Reset();return false;
    }
    SetTimeState cameraClock(timeGroup);
    const int now=gameLocal.time;
    const idAnimBlend* blend=animator.CurrentAnim(ANIMCHANNEL_ALL);
    const char* name=blend!=NULL ? blend->AnimFullName() : "";
    const float phase=blend!=NULL && blend->Length()>0 ?
        ReachCamera::Limit(float(blend->AnimTime(now))/float(blend->Length()),0,1) : 0;
    const bool sprintLoop=strstr(name,"sprint_loop")!=NULL && strstr(name,"airborne")==NULL;
    const bool authored=sprintLoop || strstr(name,"melee")!=NULL || strstr(name,"throw_grenade")!=NULL;
    ReachCamera::Profile profile=ReachCamera::None;
    if( strstr(name,"reload_empty")!=NULL ) {profile=ReachCamera::ReloadEmpty;}
    else if( strstr(name,"reload")!=NULL ) {profile=ReachCamera::Reload;}
    else if( strstr(name,"sprint_enter")!=NULL ) {profile=ReachCamera::SprintEnter;}
    else if( strstr(name,"sprint_exit")!=NULL ) {profile=ReachCamera::SprintExit;}
    else if( sprintLoop ) {profile=ReachCamera::SprintLoop;}
    else if( strstr(name,"raise")!=NULL || strstr(name,"ready")!=NULL ) {profile=ReachCamera::Raise;}
    else if( strstr(name,"putaway")!=NULL || strstr(name,"put_away")!=NULL ) {profile=ReachCamera::Lower;}
    ReachCamera::Motion target=ReachCamera::ProfileMotion(profile,phase);
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
                target.p[i]+=cameraOrigin[i]*.55f;
                target.a[i]+=idMath::AngleNormalize180(cameraAngles[i])*.65f;
            }
        }
    }
    const ReachCamera::Motion motion=reachCamera.Evaluate(now,target);
    for( int i=0;i<3;++i ) {offset[i]=motion.p[i];angles[i]=motion.a[i];}
    if( cvarSystem->GetCVarBool("reach_cameraDebug") && reachCamera.debugTime!=now )
    {
        reachCamera.debugTime=now;
        gameLocal.Printf("[ReachCamera] t=%d anim=%s phase=%.4f pos=%.5f,%.5f,%.5f ang=%.5f,%.5f,%.5f shots=%d\n",
            now,name,phase,offset.x,offset.y,offset.z,angles.pitch,angles.yaw,angles.roll,reachCamera.sequence);
    }
    return true;
}

