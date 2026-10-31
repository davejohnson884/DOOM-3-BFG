    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319"))
    {
        const int mode=spawnArgs.GetInt("_m319_latch");
        const bool tethered=mode==ReachM319::Holding || mode==ReachM319::Armed;
        const bool actor=ent->IsType(idActor::Type) || ent->IsType(idAFAttachment::Type);
        idVec3 incoming=velocity;const float speed=incoming.Normalize();
        const bool impact=ReachM319::DirectImpact(tethered,actor,speed,-incoming*collision.c.normal);
        if(!spawnArgs.GetBool("_m319_bounced")) {
            spawnArgs.SetBool("_m319_bounced",true);spawnArgs.SetInt("_m319_bounce",gameLocal.time);
            if(tethered) spawnArgs.SetInt("_m319_latch",ReachM319::Armed);
            if(!tethered && !impact) {spawnArgs.SetBool("_m319_fusePosted",true);PostEventMS(&EV_Explode,500);}
            if(cvarSystem->GetCVarBool("g_debugWeapon")) gameLocal.Printf("[ReachM319] first bounce t=%d tether=%d impact=%d\n",gameLocal.time,tethered,impact);
        }
        // Actor impact when tapped; while tethered the round bounces off actors.
        projectileFlags.detonate_on_actor=impact;
        projectileFlags.detonate_on_world=impact;
    }
