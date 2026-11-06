"""Reach-only surface-traced detonation marks; retain existing explosion FX."""
def extend(changed,replace):
 f='neo/d3xp/Player.cpp';s=changed[f]
 old='\t\tgunpos += reachMotionWeapon->spawnArgs.GetVector("reach_view_offset", reachMotionWeapon->spawnArgs.GetBool("reach_rocket") ? "3 0 -1" : "0 0 0");\n'
 new='        const idDict* reachViewDefinition=reachMotionWeapon->spawnArgs.GetBool("reach_rocket") ? gameLocal.FindEntityDefDict("weapon_rocketlauncher",false) : NULL;\n        const idDict& reachViewSettings=reachViewDefinition!=NULL ? *reachViewDefinition : reachMotionWeapon->spawnArgs;\n        gunpos += reachViewSettings.GetVector("reach_view_offset",reachMotionWeapon->spawnArgs.GetBool("reach_rocket") ? "3 0 -1" : "0 0 0");\n'
 changed[f]=replace(s,old,new,f)
 f='neo/d3xp/Projectile.cpp';s=changed[f]
 # Old saved projectile dictionaries may lack the new decal keys. Resolve
 # authored presentation from the current definition, without changing saves.
 anchor='\t// change the model, usually to a PRT\n'
 code='''    if(!common->IsMultiplayer() &&
       (spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_m319") ||
        idStr::Cmp(GetEntityDefName(),"projectile_reach_frag")==0) &&
       !spawnArgs.GetBool("_reach_blastDecalDone")) {
        spawnArgs.SetBool("_reach_blastDecalDone",true);
        const idDict* definition=gameLocal.FindEntityDefDict(GetEntityDefName(),false);
        const idDict& decalDef=definition!=NULL ? *definition : spawnArgs;
        const char* mark=decalDef.GetString("mtr_reach_blast_decal");
        if(mark[0]) {
            trace_t surface;bool found=false;float nearest=1e10f;
            const idVec3 center=collision.endpos;
            // Collision-driven rockets already have a real surface. Timed
            // fuses provide a synthetic up-normal and must query geometry.
            idEntity* hit=gameLocal.entities[collision.c.entityNum];
            if(collision.c.material!=NULL && hit!=NULL &&
               !hit->IsType(idActor::Type) && !hit->IsType(idAFAttachment::Type) &&
               !(collision.c.material->GetSurfaceFlags() & SURF_NOIMPACT)) {
                surface=collision;found=true;
            }
            if(!found) {
                const float reach=decalDef.GetFloat("reach_blast_decal_distance","48");
                const idVec3 directions[6]={idVec3(0,0,-1),idVec3(1,0,0),idVec3(-1,0,0),idVec3(0,1,0),idVec3(0,-1,0),idVec3(0,0,1)};
                for(int i=0;i<6;++i) {
                    trace_t candidate;
                    gameLocal.clip.TracePoint(candidate,center,center+reach*directions[i],MASK_SHOT_RENDERMODEL,this);
                    if(candidate.fraction>=1 || candidate.c.material==NULL ||
                       (candidate.c.material->GetSurfaceFlags() & SURF_NOIMPACT)) continue;
                    idEntity* entity=gameLocal.entities[candidate.c.entityNum];
                    if(entity==NULL || entity->IsType(idActor::Type) || entity->IsType(idAFAttachment::Type)) continue;
                    const float distance=(candidate.c.point-center).LengthSqr();
                    if(distance<nearest) {nearest=distance;surface=candidate;found=true;}
                }
            }
            if(found) {
                const float size=decalDef.GetFloat("reach_blast_decal_size","96");
                gameLocal.ProjectDecal(surface.c.point+surface.c.normal,-surface.c.normal,12,true,size,mark);
                if(cvarSystem->GetCVarBool("g_debugWeapon"))
                    gameLocal.Printf("[REACHDECAL] type=%s material=%s point=(%s) normal=(%s) size=%.1f\\n",GetEntityDefName(),mark,surface.c.point.ToString(),surface.c.normal.ToString(),size);
            } else if(cvarSystem->GetCVarBool("g_debugWeapon"))
                gameLocal.Printf("[REACHDECAL] type=%s skipped=no_nearby_surface\\n",GetEntityDefName());
        }
    }
'''
 s=replace(s,anchor,code+anchor,f)
 s=replace(s,"if( *decal != '\\0' )","if( *decal != '\\0' && !projectileDef.GetBool(\"reach_rocket\") && !projectileDef.GetBool(\"reach_m319\") && !projectileDef.GetBool(\"reach_floor_fuse\") )",f)
 changed[f]=s
 return changed
