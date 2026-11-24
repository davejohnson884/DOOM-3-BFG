    // Reach frag motion history: eight short, camera-facing beam segments follow
    // actual positions, including bounces. Entity IDs/history use saved spawnArgs.
    // Child entities expire independently if their projectile disappears.
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_frag_ballistics") && state==LAUNCHED) {
        const idVec3 position=physicsObj.GetOrigin();
        const float speed=physicsObj.GetLinearVelocity().Length();
        const int previous=spawnArgs.GetInt("_frag_sampleTime", "-1");
        if(previous<0 || gameLocal.time-previous>=16) {
            for(int j=8;j>0;--j) {
                spawnArgs.SetVector(va("_frag_point%d",j),spawnArgs.GetVector(va("_frag_point%d",j-1),position.ToString(8)));
                spawnArgs.SetInt(va("_frag_pointTime%d",j),spawnArgs.GetInt(va("_frag_pointTime%d",j-1),va("%d",gameLocal.time)));
            }
            spawnArgs.SetVector("_frag_point0",position);
            spawnArgs.SetInt("_frag_pointTime0",gameLocal.time);
            spawnArgs.SetInt("_frag_sampleTime",gameLocal.time);
        }
        const float baseWidth=idMath::ClampFloat(.05f,3.0f,spawnArgs.GetFloat("reach_frag_trail_width",".42"));
        const float baseAlpha=idMath::ClampFloat(0.0f,1.0f,spawnArgs.GetFloat("reach_frag_trail_alpha",".46"));
        for(int j=0;j<8;++j) {
            const idVec3 head=j==0 ? position : spawnArgs.GetVector(va("_frag_point%d",j),position.ToString(8));
            const int age=j==0 ? 0 : gameLocal.time-spawnArgs.GetInt(va("_frag_pointTime%d",j),va("%d",gameLocal.time));
            const float trailAge=idMath::ClampFloat(0.0f,1.0f,float(age)/130.0f);
            const idVec3 tail=spawnArgs.GetVector(va("_frag_point%d",j+1),position.ToString(8));
            idEntityPtr<idEntity> reference;reference.SetSpawnId(spawnArgs.GetInt(va("_frag_beam%d",j)));
            idEntity* beam=reference.GetEntity();
            if(age>=130 || (head-tail).LengthSqr()<.25f || speed<35.0f) {if(beam!=NULL)beam->Hide();continue;}
            if(beam==NULL) {
                idDict args;args.Set("model","_BEAM");args.SetBool("networkSync",false);
                beam=gameLocal.SpawnEntityType(idStaticEntity::Type,&args);
                if(beam==NULL)continue;
                reference=beam;spawnArgs.SetInt(va("_frag_beam%d",j),reference.GetSpawnId());
            }
            beam->CancelEvents(&EV_Remove);beam->PostEventMS(&EV_Remove,250);
            beam->GetPhysics()->SetOrigin(head);beam->GetPhysics()->SetAxis(mat3_identity);
            renderEntity_t* re=beam->GetRenderEntity();re->customShader=declManager->FindMaterial("reach/frag/fx/contrail");
            re->noShadow=re->noSelfShadow=re->noOverlays=true;
            re->shaderParms[SHADERPARM_BEAM_END_X]=tail.x;
            re->shaderParms[SHADERPARM_BEAM_END_Y]=tail.y;
            re->shaderParms[SHADERPARM_BEAM_END_Z]=tail.z;
            re->shaderParms[SHADERPARM_BEAM_WIDTH]=baseWidth*(1.0f-.8f*trailAge);
            const float fade=(1.0f-trailAge)*idMath::ClampFloat(0.0f,1.0f,speed/120.0f);
            re->shaderParms[SHADERPARM_RED]=1.0f;
            re->shaderParms[SHADERPARM_GREEN]=.96f;
            re->shaderParms[SHADERPARM_BLUE]=.85f;
            re->shaderParms[SHADERPARM_ALPHA]=baseAlpha*fade;
            beam->Show();beam->UpdateVisuals();beam->Present();
        }
        if(cvarSystem->GetCVarBool("g_debugWeapon") && gameLocal.time>=spawnArgs.GetInt("_frag_nextTrace")) {
            spawnArgs.SetInt("_frag_nextTrace",gameLocal.time+50);
            gameLocal.Printf("[FRAGFLIGHT] SAMPLE time=%d position=(%s) velocity=(%s)\n",gameLocal.time,position.ToString(4),physicsObj.GetLinearVelocity().ToString(4));
        }
    }
