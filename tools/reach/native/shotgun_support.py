"""Extend the tested Reach controller to an opt-in pump shotgun."""
from pathlib import Path
def extend(changed,replace):
    weapon='neo/d3xp/Weapon.cpp';player='neo/d3xp/Player.cpp';header='neo/d3xp/Weapon.h'
    w=changed[weapon]
    # Add a third explicit gameplay/model identity, retaining the exact old paths.
    for prefix in ['spawnArgs','args']:
        expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_magnum" ) == 0'
        assert expr in w
        w=w.replace(expr,'( '+expr+' || '+expr.replace('viewmodel_reach_magnum','viewmodel_reach_shotgun')+' )')
    needle='\tassert( modelname );\n'
    w=replace(w,needle,needle+'''    if(!common->IsMultiplayer() && idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_shotgun")==0 &&
        idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) {modelname="viewmodel_reach_shotgun_present";}
''',weapon)
    # A press during insertion is buffered until the current shell is seated.
    w=replace(w,'        WEAPON_ATTACK=press;','''        if(press && spawnArgs.GetBool("reach_shell_reload") && spawnArgs.GetInt("_reach_shellPhase")!=0)
            spawnArgs.SetBool("_reach_shellInterrupt",true);
        WEAPON_ATTACK=press;''',weapon)
    w=replace(w,'void idWeapon::Event_WeaponState( const char* statename, int blendFrames )\n{\n','''void idWeapon::Event_WeaponState( const char* statename, int blendFrames )
{
    if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload") &&
        idStr::Cmp(statename,"Idle")==0 && spawnArgs.GetBool("_reach_shellFireQueued"))
    {spawnArgs.SetBool("_reach_shellFireQueued",false);if(ammoClip.Get()>0) {statename="Fire";}}
''',weapon)
    w=replace(w,'void idWeapon::Event_AddToClip( int amount )\n{\n','''void idWeapon::Event_AddToClip( int amount )
{
    if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload") &&
        spawnArgs.GetBool("_reach_shellOwnsAmmo") && !spawnArgs.GetBool("_reach_insertingShell")) {return;}
''',weapon)
    w=replace(w,'void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{\n','''void idWeapon::Event_PlayAnim( int channel, const char* animname )
{
    if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload") && channel==ANIMCHANNEL_ALL)
    {
        const bool reload=idStr::Cmp(animname,"reload_full")==0 || idStr::Cmp(animname,"reload_empty")==0;
        spawnArgs.SetBool("_reach_shellOwnsAmmo",reload);
        spawnArgs.SetInt("_reach_shellPhase",reload ? 1 : 0);
        spawnArgs.SetBool("_reach_shellInterrupt",false);
        spawnArgs.SetBool("_reach_shellFireQueued",false);
        if(reload) {spawnArgs.SetBool("_reach_shellStartedEmpty",ammoClip.Get()==0);animname="reload_enter";}
    }
''',weapon)
    w=replace(w,'void idWeapon::Event_PlayCycle( int channel, const char* animname )\n{\n','''void idWeapon::Event_PlayCycle( int channel, const char* animname )
{
    if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload") && channel==ANIMCHANNEL_ALL)
    {spawnArgs.SetBool("_reach_shellOwnsAmmo",false);spawnArgs.SetInt("_reach_shellPhase",0);}
''',weapon)
    w=replace(w,'void idWeapon::Event_AnimDone( int channel, int blendFrames )\n{\n','''void idWeapon::Event_AnimDone( int channel, int blendFrames )
{
    if(ReachShellReload(channel)) {return;}
''',weapon)
    needle='void idWeapon::Event_LaunchProjectiles( int num_projectiles, float spread, float fuseOffset, float launchPower, float dmgPower )\n{\n'
    w=replace(w,needle,needle+'''    if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload"))
        num_projectiles=idMath::ClampInt(1,32,spawnArgs.GetInt("reach_pellet_count","1"));
''',weapon)
    w=replace(w,'\t\t\tdir.Normalize();\n\n\t\t\tif( projectileEnt )','''            if(!common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_shell_reload"))
            {
                // Equal-area cone: source projection uses15 pellets, exponent.5,
                // four-degree half-angle. Rotate the distribution once per shot.
                const float radius=idMath::Tan(DEG2RAD(spawnArgs.GetFloat("reach_pellet_spread","4")))*
                    idMath::Sqrt((float(i)+.5f)/float(num_projectiles));
                const float theta=2.39996323f*float(i)+renderEntity.shaderParms[SHADERPARM_DIVERSITY]*idMath::PI;
                dir=muzzleAxis[0]+muzzleAxis[2]*(radius*idMath::Sin(theta))-
                    muzzleAxis[1]*(radius*idMath::Cos(theta));
            }
\t\t\tdir.Normalize();

\t\t\tif( projectileEnt )''',weapon)
    w=replace(w,'static bool ReachCombatWeapon( const idDict& args )\n',
        (Path(__file__).parent/'ReachShellReload.cpp').read_text()+'\nstatic bool ReachCombatWeapon( const idDict& args )\n',weapon)
    changed[weapon]=w
    h=changed[header];needle='bool ReachCameraMotion'
    assert h.count(needle)==1
    changed[header]=h.replace(needle,'bool                    ReachShellReload( int channel );\n\t'+needle)
    p=changed[player];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_magnum" ) == 0'
    assert p.count(expr)==1
    changed[player]=p.replace(expr,'( '+expr+' || '+expr.replace('viewmodel_reach_magnum','viewmodel_reach_shotgun')+' )')
    return changed
