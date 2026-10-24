    if( ReachCombatWeapon(spawnArgs) )
    {
        const renderView_t* view=owner->GetRenderView();
        const float scale=view!=NULL ? ReachMuzzle::WorldSmokeScale(
            cvarSystem->GetCVarFloat("r_reachWeaponFov"),view->fov_y) : 1.0f;
        const idVec3 relative=origin-playerViewOrigin;
        origin=playerViewOrigin+playerViewAxis[0]*(relative*playerViewAxis[0])+
            scale*(playerViewAxis[1]*(relative*playerViewAxis[1])+playerViewAxis[2]*(relative*playerViewAxis[2]));
    }
