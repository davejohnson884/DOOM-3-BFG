"""Extend the same saved controller to the opted-in Repeater only."""
from pathlib import Path
def extend(changed,replace):
 root=Path(__file__).parent;w=changed['neo/d3xp/Weapon.cpp'];p=changed['neo/d3xp/Player.cpp'];f='neo/d3xp/Weapon.cpp'
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_plasma_repeater')+' )')
 expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0'
 assert expr in p;changed['neo/d3xp/Player.cpp']=p.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_plasma_repeater')+' )')
 w=replace(w,'#include "ReachWeaponActions.h"','#include "ReachWeaponActions.h"\n#include "ReachRepeaterHeat.h"',f)
 w=replace(w,'\tassert( modelname );\n','\tassert( modelname );\n    if(ReachRepeaterWeapon() && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) {modelname="viewmodel_reach_plasma_repeater_present";}\n',f)
 w=replace(w,'\tif( idealState.Length() )\n\t{\n\t\tSetState( idealState, animBlendFrames );','    ReachRepeaterUpdate();\n\tif( idealState.Length() )\n\t{\n\t\tSetState( idealState, animBlendFrames );',f)
 w=replace(w,'void idWeapon::Event_AmmoInClip()\n{','void idWeapon::Event_AmmoInClip()\n{\n    if(ReachRepeaterWeapon()) {idThread::ReturnFloat(owner->inventory.HasAmmo(ammoType,1));return;}',f)
 w=replace(w,'void idWeapon::Event_AddToClip( int amount )\n{','void idWeapon::Event_AddToClip( int amount )\n{\n    if(ReachRepeaterWeapon()) {return;} // Venting never creates energy.',f)
 w=replace(w,'\tammoClip = ammoinclip;','''    if(ReachRepeaterWeapon() && clipSize==0 && ammoinclip>0) {
        // Transfer a pre-port Chaingun magazine back to the finite inventory
        // once; the new no-magazine slot subsequently stores clip zero.
        owner->inventory.SetInventoryAmmoForType(ammoType,owner->inventory.HasAmmo(ammoType,1)+ammoinclip);
        ammoinclip=0;
    }
\tammoClip = ammoinclip;''',f)
 w=replace(w,'void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{','''void idWeapon::Event_PlayAnim( int channel, const char* animname )
{
    if(ReachRepeaterWeapon() && channel==ANIMCHANNEL_ALL) {
        ReachRepeaterUpdate();const bool vent=idStr::Cmp(animname,"reload_full")==0 || idStr::Cmp(animname,"reload_empty")==0;
        if(vent) {
            spawnArgs.SetInt("_reach_ventPhase",1);animname="vent_enter";
            Event_StartWeaponParticle("reach_vent1");Event_StartWeaponParticle("reach_vent2");
            if(cvarSystem->GetCVarBool("g_debugWeapon")) {gameLocal.Printf("[ReachRepeater] VENT_BEGIN heat=%.5f battery=%d\\n",owner->spawnArgs.GetFloat("_reach_repeaterHeat"),owner->inventory.HasAmmo(ammoType,1));}
        } else {spawnArgs.SetInt("_reach_ventPhase",0);Event_StopWeaponParticle("reach_vent1");Event_StopWeaponParticle("reach_vent2");}
    }
''',f)
 w=replace(w,'    if(ReachShellReload(channel)) {return;}','    if(ReachRepeaterAnimDone(channel)) {return;}\n    if(ReachShellReload(channel)) {return;}',f)
 anchor='\t// Predict clip ammo on locally controlled MP clients.'
 w=replace(w,anchor,'    if(!ReachRepeaterShot()) {return;}\n'+anchor,f)
 w+='\n'+(root/'ReachRepeater.cpp').read_text();changed[f]=w
 h='neo/d3xp/Weapon.h';changed[h]=replace(changed[h],'\tbool                    ReachShellReload( int channel );','\tbool                    ReachShellReload( int channel );\n    bool ReachRepeaterWeapon() const;\n    void ReachRepeaterUpdate();\n    bool ReachRepeaterShot();\n    bool ReachRepeaterAnimDone(int channel);',h)
 return changed
