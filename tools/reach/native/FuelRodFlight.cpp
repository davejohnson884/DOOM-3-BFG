// Doom corridor adaptation: .10 s launch phase; retain the existing ignition burst and mature effect.
// All state uses the saved spawn dictionary; no script or save-layout change.
int fuelLaunch=spawnArgs.GetInt("_fuel_launchTime","-1");
if(fuelLaunch<0) {
    // A v1 projectile was already using the mature effect. Do not replay ignition.
    fuelLaunch=gameLocal.time-130;spawnArgs.SetInt("_fuel_launchTime",fuelLaunch);
    spawnArgs.SetBool("_fuel_ignited",true);
}
const int fuelAge=gameLocal.time>=fuelLaunch ? gameLocal.time-fuelLaunch : 0;
const float fuelMaturity=ReachFuelRod::Maturity(fuelAge);
renderEntity.shaderParms[7]=fuelMaturity;
const float fuelFlash=1.0f-idMath::Fabs(float(fuelAge-100))/35.0f;
renderEntity.shaderParms[8]=fuelFlash>0 ? fuelFlash : 0;
const idVec3 fuelBaseColor=spawnArgs.GetVector("light_color","1 2.1 .16");
const float fuelLightGain=.20f+.80f*fuelMaturity;
renderLight.shaderParms[0]=fuelBaseColor.x*fuelLightGain;
renderLight.shaderParms[1]=fuelBaseColor.y*fuelLightGain;
renderLight.shaderParms[2]=fuelBaseColor.z*fuelLightGain;
renderLight.lightRadius.Set(72+64*fuelMaturity,72+64*fuelMaturity,72+64*fuelMaturity);
if(!spawnArgs.GetBool("_fuel_ignited") && ReachFuelRod::Ignited(fuelAge)) {
    spawnArgs.SetBool("_fuel_ignited",true);
    const char* fuelMatureTrail=spawnArgs.GetString("smoke_fly_mature","reach_fuelrod_trail.prt");
    smokeFly=static_cast<const idDeclParticle*>(declManager->FindType(DECL_PARTICLE,fuelMatureTrail));
    smokeFlyTime=gameLocal.time;spawnArgs.Set("smoke_fly",fuelMatureTrail);
    const idVec3 fuelIgnitionOrigin=physicsObj.GetOrigin();
    const idMat3 fuelIgnitionAxis=physicsObj.GetAxis();
    const char* fuelIgnitionFx=spawnArgs.GetString("fx_reach_fuel_ignite","reach_fuelrod_ignition");
    if(fuelIgnitionFx[0]) idEntityFx::StartFx(fuelIgnitionFx,&fuelIgnitionOrigin,&fuelIgnitionAxis,NULL,false);
    if(cvarSystem->GetCVarBool("g_debugWeapon"))
        gameLocal.Printf("[FUELSTAGE] IGNITE time=%d age=%d distance=%.2f\n",gameLocal.time,fuelAge,spawnArgs.GetFloat("_fuel_distance"));
}
UpdateVisuals();

