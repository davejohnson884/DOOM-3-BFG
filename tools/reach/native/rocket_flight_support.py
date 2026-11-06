"""M41-only presentation offset and owned flight/detonation light lifetime."""
def extend(changed,replace):
 f='neo/d3xp/Player.cpp';s=changed[f]
 anchor='\t\torigin = viewOrigin + gunpos * viewAxis;\n'
 s=replace(s,anchor,'\t\tgunpos += reachMotionWeapon->spawnArgs.GetVector("reach_view_offset", reachMotionWeapon->spawnArgs.GetBool("reach_rocket") ? "3 0 -1" : "0 0 0");\n'+anchor,f);changed[f]=s
 f='neo/d3xp/Projectile.cpp';s=changed[f]
 # Use a unique light ID to keep the rocket shell from shadowing its motor
 # light. Environmental geometry still casts shadows normally.
 anchor='\tspawnArgs.GetVector( "light_offset", "0 0 0", lightOffset );\n'
 s=replace(s,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket")) {
        renderLight.lightId=entityNumber+1;
        renderEntity.suppressShadowInLightID=renderLight.lightId;
    }
'''+anchor,f)
 # The flight emitter must be released even when no stock explosion shader
 # was selected. The explosion starts a separate, bounded light lifetime.
 anchor='\t// explosion light\n\tlight_shader = spawnArgs.GetString( "mtr_explode_light_shader" );\n'
 s=replace(s,anchor,'''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket")) {
        if(lightDefHandle!=-1) {gameRenderWorld->FreeLightDef(lightDefHandle);lightDefHandle=-1;}
        renderLight.lightRadius.Zero();
        spawnArgs.SetVector("_rocket_blastLightOrigin",collision.endpos+12.0f*collision.c.normal);
        if(cvarSystem->GetCVarBool("g_debugWeapon"))
            gameLocal.Printf("[ROCKETLIGHT] IMPACT time=%d flightReleased=1\\n",gameLocal.time);
    }
'''+anchor,f)
 anchor='\t// add the light\n\tif( renderLight.lightRadius.x > 0.0f && g_projectileLights.GetBool() )\n'
 s=replace(s,anchor,'''    const bool reachRocketLight=!common->IsMultiplayer() && spawnArgs.GetBool("reach_rocket");
    // Test elapsed time, not whether a frame landed exactly on the endpoint.
    // The material owns the source color/intensity envelope; this owns cleanup.
    if(reachRocketLight && (state==FIZZLED ||
       (state==EXPLODED && lightEndTime<=gameLocal.time))) {
        if(lightDefHandle!=-1) {
            gameRenderWorld->FreeLightDef(lightDefHandle);lightDefHandle=-1;
            if(cvarSystem->GetCVarBool("g_debugWeapon"))
                gameLocal.Printf("[ROCKETLIGHT] END time=%d deadline=%d\\n",gameLocal.time,lightEndTime);
        }
        renderLight.lightRadius.Zero();
    }
'''+anchor,f)
 anchor='\t\trenderLight.axis = GetPhysics()->GetAxis();\n'
 s=replace(s,anchor,anchor+'''        if(reachRocketLight && state==EXPLODED) {
            renderLight.origin=spawnArgs.GetVector("_rocket_blastLightOrigin");
            renderLight.axis=mat3_identity;
        }
''',f)
 s=replace(s,'if( lightEndTime > 0 && gameLocal.time <= lightEndTime )','if( !reachRocketLight && lightEndTime > 0 && gameLocal.time <= lightEndTime )',f)
 anchor='\t\t\tlightDefHandle = gameRenderWorld->AddLightDef( &renderLight );\n'
 s=replace(s,anchor,anchor+'''            if(reachRocketLight && cvarSystem->GetCVarBool("g_debugWeapon"))
                gameLocal.Printf("[ROCKETLIGHT] START time=%d phase=%s end=%d origin=(%s)\\n",gameLocal.time,state==LAUNCHED ? "flight" : "blast",lightEndTime,renderLight.origin.ToString());
''',f)
 changed[f]=s
 return changed
