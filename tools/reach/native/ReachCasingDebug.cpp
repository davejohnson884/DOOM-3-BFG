    if( ReachCombatWeapon(spawnArgs) && cvarSystem->GetCVarBool("reach_polishDebug") )
    {
        const idVec3 relative=origin-playerViewOrigin;
        const idVec3 local(relative*playerViewAxis[0],relative*playerViewAxis[1],relative*playerViewAxis[2]);
        gameLocal.Printf("[ReachCasing] t=%d model=%s local=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f\n",
            gameLocal.time,brassDict.GetString("model"),local.x,local.y,local.z,
            linear_velocity*playerViewAxis[0],linear_velocity*playerViewAxis[1],linear_velocity*playerViewAxis[2]);
    }
