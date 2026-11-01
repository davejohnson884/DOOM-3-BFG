"""M319 grenade-slot integration; existing scripts and save fields remain unchanged."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';w=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_m37" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_m37','reach_m319')+' )')
 p=changed['neo/d3xp/Player.cpp'];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_m37" ) == 0';assert expr in p;changed['neo/d3xp/Player.cpp']=p.replace(expr,'( '+expr+' || '+expr.replace('reach_m37','reach_m319')+' )')
 w=replace(w,'\tassert( modelname );\n','\tassert( modelname );\n    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319") && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) {modelname="viewmodel_reach_m319_present";}\n',f)
 w=replace(w,'void idWeapon::PresentWeapon( bool showViewModel )\n{\n','''void idWeapon::PresentWeapon( bool showViewModel )
{
    // Upgrade a legacy save only after all restored entities/threads exist.
    // Rebuild through the supported weapon constructor, never reinterpret a
    // serialized handgrenade script object as the shared Reach controller.
    if(!common->IsMultiplayer() && owner!=NULL && weaponDef!=NULL &&
       idStr::Cmp(weaponDef->GetName(),"weapon_handgrenade")==0 && weaponDef->dict.GetBool("reach_m319") &&
       idStr::Cmp(scriptObject.GetTypeName(),"weapon_handgrenade")==0)
    {
        GetWeaponDef("weapon_handgrenade",-1);
        gameLocal.Printf("[ReachM319] legacy grenade weapon refreshed through constructor\\n");
    }
    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_m319"))
    {
        if(spawnArgs.GetBool("_m319_autoReload") && idStr::Cmp(state.c_str(),"Idle")==0 &&
           (owner->usercmd.buttons&BUTTON_ATTACK)==0 && ammoClip.Get()==0 &&
           owner->inventory.HasAmmo(ammoType,ammoRequired)>0 && session->GetActingGameStateLobbyBase().GetLobbyUserWeaponAutoReload(gameLocal.lobbyUserIDs[owner->entityNumber]))
            WEAPON_RELOAD=true;
    }
''',f)
 w=replace(w,'void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{\n','''void idWeapon::Event_PlayAnim( int channel, const char* animname )
{
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319") && channel==ANIMCHANNEL_ALL) {
        if(idStr::Cmp(animname,"fire")==0) spawnArgs.SetBool("_m319_autoReload",true);
        if(strstr(animname,"reload")!=NULL) spawnArgs.SetBool("_m319_autoReload",false);
    }
''',f)
 # This shared-script event sets the AR's ammo counter. The M319 screen reports
 # live tether range in metres; it must not become a one-round ammo display.
 w=replace(w,'\t// update the weapon script\n\tUpdateScript();\n','''\t// update the weapon script
\tUpdateScript();
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) {
        const bool live=spawnArgs.GetInt("_m319_displayUntil")>=gameLocal.time && spawnArgs.GetBool("_m319_displayTether");
        const int range=live ? idMath::ClampInt(0,999,int(spawnArgs.GetFloat("_m319_range"))) : 0;
        renderEntity.shaderParms[8]=float((range/100)%10);
        renderEntity.shaderParms[9]=float((range/10)%10);
        renderEntity.shaderParms[10]=float(range%10);
        renderEntity.shaderParms[11]=spawnArgs.GetInt("_m319_displayUntil")>=gameLocal.time ? float(spawnArgs.GetInt("_m319_status")) : 0.0f;
    }
''',f)
 w=replace(w,'int\tidWeapon::GetZoomFov()\n{\n','''int\tidWeapon::GetZoomFov()
{
    if(!common->IsMultiplayer() && owner!=NULL && spawnArgs.GetBool("reach_m319")) return int(owner->DefaultFov());
''',f)
 changed[f]=w
 f='neo/d3xp/Projectile.cpp';p=changed[f]
 from pathlib import Path
 root=Path(__file__).resolve().parent
 p=replace(p,'#include "ReachQuickActions.h"','#include "ReachQuickActions.h"\n#include "ReachM319Policy.h"',f)
 p=replace(p,'void idProjectile::Think()\n{\n','void idProjectile::Think()\n{\n'+(root/'M319Think.cpp').read_text(),f)
 p=replace(p,'\tlaunchOrigin = start;\n','''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) {
        spawnArgs.SetInt("_m319_launch",gameLocal.time);spawnArgs.SetInt("_m319_latch",ReachM319::Holding);
        spawnArgs.SetBool("_m319_bounced",false);spawnArgs.SetBool("_m319_fusePosted",false);
        spawnArgs.SetFloat("_m319_distance",0);spawnArgs.SetVector("_m319_prev",start);
    }
\tlaunchOrigin = start;
''',f)
 p=replace(p,'\t// direction of projectile\n',(root/'M319Collision.cpp').read_text()+'\t// direction of projectile\n',f)
 # Keep the latch controller awake independently of the rigid body.
 start=p.index('void idProjectile::Launch(');end=p.index('void idProjectile::Think()',start)
 launch=p[start:end]
 launch=replace(launch,'\tstate = LAUNCHED;\n','''\tstate = LAUNCHED;
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) BecomeActive(TH_THINK);
''',f)
 launch=replace(launch,'\tphysicsObj.SetMass( mass );\n','''    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) {
        // Small, rounded collision volume. Do not let a spinning flat cylinder
        // launch sideways from floor seams and narrow door frames.
        idTraceModel shape;shape.SetupDodecahedron(idBounds(idVec3(-1.4f,-1.4f,-1.4f),idVec3(1.4f,1.4f,1.4f)));
        physicsObj.SetClipModel(new idClipModel(shape),1.0f);
        physicsObj.GetClipModel()->SetOwner(owner.GetEntity());
    }
\tphysicsObj.SetMass( mass );
''',f)
 launch=replace(launch,'\tphysicsObj.SetLinearVelocity( axis[ 2 ] * speed + pushVelocity );','''\tphysicsObj.SetLinearVelocity( axis[ 2 ] * speed +
        ((!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) ? pushVelocity*.35f : pushVelocity) );''',f)
 p=p[:start]+launch+p[end:]
 start=p.index('void idProjectile::Restore(');end=p.index('void idProjectile::',start+10)
 restored=p[start:end];at=restored.rfind('}');assert at>0
 restored=restored[:at]+'''    // Also repair an already-settled linked round loaded from a v1 save.
    if(!common->IsMultiplayer() && state==LAUNCHED && spawnArgs.GetBool("reach_m319")) BecomeActive(TH_THINK);
'''+restored[at:];p=p[:start]+restored+p[end:]
 changed[f]=p
 f='neo/d3xp/Player.cpp';p=changed[f]
 p=replace(p,'void idPlayer::UpdateWeapon()\n{\n','''void idPlayer::UpdateWeapon()
{
    // The grenade slot now holds a rifle-sized launcher. Use the supported
    // two-hand host posture while retaining the original inventory slot.
    if(!common->IsMultiplayer() && weapon.GetEntity()!=NULL && weapon.GetEntity()->spawnArgs.GetBool("reach_m319"))
        animPrefix="chaingun";
''',f)
 changed[f]=p;return changed
