"""Opt-in Reach frag launch, bounded motion ribbon and deterministic bounce."""
from pathlib import Path

def extend(changed,replace):
    root=Path(__file__).resolve().parent
    f='neo/d3xp/Weapon.cpp';s=changed[f]
    old='\tconst idVec3 direction = playerViewAxis[0];\n\tfrag->Create( owner, playerViewOrigin, direction );'
    new='''    idVec3 direction=playerViewAxis[0];
    if(fragDef->dict.GetBool("reach_frag_ballistics")) {
        const float vertical=direction.z;
        const float lift=DEG2RAD(fragDef->dict.GetFloat("reach_throw_lift","6"))*(1.0f-vertical*vertical);
        direction=direction*idMath::Cos(lift)+playerViewAxis[2]*idMath::Sin(lift);
        direction.Normalize();
    }
\tfrag->Create( owner, playerViewOrigin, direction );'''
    s=replace(s,old,new,f);changed[f]=s
    f='neo/d3xp/Projectile.cpp';s=changed[f]
    old='\tphysicsObj.SetMass( mass );\n'
    new='''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_frag_ballistics")) {
        idTraceModel shape;shape.SetupDodecahedron(idBounds(idVec3(-2.6f,-2.6f,-2.6f),idVec3(2.6f,2.6f,2.6f)));
        physicsObj.SetClipModel(new idClipModel(shape),1.0f);
        physicsObj.GetClipModel()->SetOwner(owner.GetEntity());
    }
'''+old
    a=s.index('void idProjectile::Launch(');b=s.index('void idProjectile::Think()',a)
    launch=s[a:b];launch=replace(launch,old,new,f);s=s[:a]+launch+s[b:]
    a=s.index('void idProjectile::Think()\n');b=s.index('void idProjectile::AddParticlesAndLight()',a)
    think=s[a:b];anchor='\tDecayOriginAndAxisDelta();'
    think=replace(think,anchor,(root/'FragFlightThink.cpp').read_text()+'\n'+anchor,f)
    s=s[:a]+think+s[b:]
    s=replace(s,'\t// Reach opt-in weapon projection / source-tag frag fuse.',(root/'FragFlightBounce.cpp').read_text()+'\t// Reach opt-in weapon projection / source-tag frag fuse.',f)
    old='spawnArgs.GetBool("reach_needle_shard"))) BecomeActive(TH_THINK);'
    s=replace(s,old,old.replace(')))',' ) || spawnArgs.GetBool("reach_frag_ballistics")))'),f)
    cleanup='''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_frag_ballistics")) {
        for(int j=0;j<8;++j) {
            idEntityPtr<idEntity> beam;beam.SetSpawnId(spawnArgs.GetInt(va("_frag_beam%d",j)));
            if(beam.GetEntity()!=NULL)beam.GetEntity()->PostEventMS(&EV_Remove,0);
            spawnArgs.SetInt(va("_frag_beam%d",j),0);
        }
    }
'''
    for signature in ['void idProjectile::Explode( const trace_t& collision, idEntity* ignore )','void idProjectile::Fizzle()']:
        anchor=signature+'\n{\n';s=replace(s,anchor,anchor+cleanup,f)
    changed[f]=s
    return changed
