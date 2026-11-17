"""Frag-only visual composition through the established soft-particle ABI."""
def extend(changed,replace):
    # Use the shared visual spawn hook without enabling launcher physics,
    # latch/input controllers, damage changes or any public save-format change.
    f='neo/d3xp/Projectile.cpp';s=changed[f]
    old='if(!common->IsMultiplayer() && (spawnArgs.GetBool("reach_m319") || spawnArgs.GetBool("reach_rocket"))) {\n        const char* visualFx='
    new=old.replace('spawnArgs.GetBool("reach_rocket")','spawnArgs.GetBool("reach_rocket") || spawnArgs.GetBool("reach_frag_fx")')
    s=replace(s,old,new,f);changed[f]=s
    # Prepare scene depth before any custom frag stage is bound, select the
    # correct MSAA program, retain linear BC7 artwork and independent seeds.
    for f in ['neo/renderer/Image_load.cpp','neo/renderer/RenderBackend.cpp','neo/renderer/Model_prt.cpp']:
        s=changed[f]
        if f.endswith('Image_load.cpp'):
            old='!idStr::Icmpn(imgName.c_str(),"textures/reach/needle_rifle/fx/",sizeof("textures/reach/needle_rifle/fx/")-1)'
            extra=old.replace('textures/reach/needle_rifle/fx/','textures/reach/frag/fx/')
        elif f.endswith('RenderBackend.cpp'):
            old='!idStr::Icmpn(shader->GetName(),"reach/needle_rifle/",19)'
            extra='!idStr::Icmpn(shader->GetName(),"reach/frag/fx/",14)'
        else:
            old='!idStr::Icmpn(stage->material->GetName(),"reach/needle_rifle/fx/",22)'
            extra='!idStr::Icmpn(stage->material->GetName(),"reach/frag/fx/",14)'
        s=replace(s,old,'('+old+' || '+extra+')',f);changed[f]=s
    return changed
