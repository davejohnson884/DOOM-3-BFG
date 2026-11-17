    // Source response separates tangential and normal loss. The rigid body's
    // default impulse has already run; replace only the opted-in frag response.
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_frag_ballistics") &&
       ent!=NULL && !ent->IsType(idActor::Type) && !ent->IsType(idAFAttachment::Type)) {
        const idVec3 surfaceVelocity=ent->GetPhysics()->GetLinearVelocity();
        const idVec3 incoming=velocity-surfaceVelocity;
        const float normalSpeed=incoming*collision.c.normal;
        if(normalSpeed<0.0f) {
            const float incidence=-normalSpeed/(incoming.Length()>1.0f ? incoming.Length() : 1.0f);
            // Source default: .5 tangent friction/.7 normal friction; steep
            // contacts use .42/.75 and .42/.82. Preserve the retained fractions.
            const float tangentRetention=incidence>.76604444f ? .58f : .5f;
            const float normalRetention=incidence>.98480775f ? .18f : (incidence>.76604444f ? .25f : .3f);
            idVec3 outgoing=(incoming-normalSpeed*collision.c.normal)*tangentRetention;
            if(-normalSpeed>65.0f)outgoing-=normalSpeed*normalRetention*collision.c.normal;
            physicsObj.SetLinearVelocity(outgoing+surfaceVelocity);
            physicsObj.SetAngularVelocity(physicsObj.GetAngularVelocity()*.35f);
            if(cvarSystem->GetCVarBool("g_debugWeapon"))
                gameLocal.Printf("[FRAGFLIGHT] BOUNCE time=%d normal=(%s) incoming=(%s) outgoing=(%s)\n",gameLocal.time,collision.c.normal.ToString(4),incoming.ToString(4),outgoing.ToString(4));
        }
    }

