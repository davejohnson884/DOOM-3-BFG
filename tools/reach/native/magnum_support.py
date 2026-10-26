"""Extend only the opted-in Reach weapon family; retain AR scripts/save bytecode."""
def extend(changed, replace):
    weapon='neo/d3xp/Weapon.cpp';player='neo/d3xp/Player.cpp'
    w=changed[weapon]
    for expr in ['idStr::Cmp( spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0',
                 'idStr::Cmp( args.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0']:
        assert expr in w
        w=w.replace(expr,'( '+expr+' || '+expr.replace('viewmodel_reach_ar','viewmodel_reach_magnum')+' )')
    w=replace(w,'#include "ReachQuickActions.h"','#include "ReachQuickActions.h"\n#include "ReachWeaponActions.h"',weapon)
    # The unchanged shared script requests its original model name. Redirect only
    # the Magnum instance; AR strings/pose and all script bytes stay unchanged.
    w=replace(w,'\tassert( modelname );\n','''\tassert( modelname );
    if( !common->IsMultiplayer() &&
        idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_magnum")==0 &&
        idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0 )
    {
        modelname="viewmodel_reach_magnum_present";
    }
''',weapon)
    w=replace(w,'\tWEAPON_ATTACK = true;\n','''    if( !common->IsMultiplayer() && ReachCombatWeapon(spawnArgs) && spawnArgs.GetBool("reach_semi_auto") )
    {
        bool consumed=spawnArgs.GetBool("_reach_triggerConsumed");
        const bool press=ReachActions::Press(consumed,true);
        spawnArgs.SetBool("_reach_triggerConsumed",consumed);
        WEAPON_ATTACK=press;
        return;
    }
\tWEAPON_ATTACK = true;
''',weapon)
    w=replace(w,'void idWeapon::EndAttack()\n{\n','''void idWeapon::EndAttack()
{
    // Release also clears the edge while a reload/switch is in progress.
    if( spawnArgs.GetBool("reach_semi_auto") ) {spawnArgs.SetBool("_reach_triggerConsumed",false);}
''',weapon)
    w=replace(w,'args.Set( "model", "reach_ar_flash_r15.prt" );','args.Set( "model", spawnArgs.GetString("reach_fp_flash_particle","reach_ar_flash_r15.prt") );',weapon)
    w=replace(w,'strcpy( fpParticle.particlename, "reach_ar_flash_r15.prt" );','idStr::Copynz( fpParticle.particlename, spawnArgs.GetString("reach_fp_flash_particle","reach_ar_flash_r15.prt"), sizeof(fpParticle.particlename) );',weapon)
    changed[weapon]=w
    p=changed[player];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_ar" ) == 0'
    assert p.count(expr)==1
    changed[player]=p.replace(expr,'( '+expr+' || '+expr.replace('viewmodel_reach_ar','viewmodel_reach_magnum')+' )')
    return changed
