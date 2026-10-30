"""M37 family wiring; no new saved fields or shared-script edits."""
def extend(changed,replace):
 f='neo/d3xp/Weapon.cpp';w=changed[f]
 for prefix in ['spawnArgs','args']:
  expr='idStr::Cmp( '+prefix+'.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0'
  assert expr in w;w=w.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_m37')+' )')
 p=changed['neo/d3xp/Player.cpp'];expr='idStr::Cmp( reachMotionWeapon->spawnArgs.GetString( "model_view" ), "viewmodel_reach_shotgun" ) == 0';assert expr in p;changed['neo/d3xp/Player.cpp']=p.replace(expr,'( '+expr+' || '+expr.replace('reach_shotgun','reach_m37')+' )')
 w=replace(w,'\tassert( modelname );\n','\tassert( modelname );\n    if(!common->IsMultiplayer() && idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0 && idStr::Cmp(modelname,"viewmodel_reach_ar_present")==0) {modelname="viewmodel_reach_m37_present";}\n',f)
 w=replace(w,'void idWeapon::Event_PlayAnim( int channel, const char* animname )\n{','''void idWeapon::Event_PlayAnim( int channel, const char* animname )
{
    if(!common->IsMultiplayer() && owner!=NULL && channel==ANIMCHANNEL_ALL &&
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0) {
        // Author's v2 graph keyframes, not the AR's magazine timing.
        if(idStr::Cmp(animname,"reload_empty")==0) {spawnArgs.SetFloat("reach_reload_fill_time",spawnArgs.GetFloat("reach_m37_empty_fill","3.3333333"));}
        else if(idStr::Cmp(animname,"reload_full")==0) {spawnArgs.SetFloat("reach_reload_fill_time",spawnArgs.GetFloat("reach_m37_full_fill","2.6666667"));}
        if(idStr::Cmp(animname,"raise")==0 && !owner->spawnArgs.GetBool("_reach_m37Readied")) {
            owner->spawnArgs.SetBool("_reach_m37Readied",true);animname="ready_initial";
        }
    }
''',f)
 # Allow the restored visual recovery tail to finish while idle. Holding fire
 # may still interrupt at the first draft's graph-ready time, after ammo fill.
 w=replace(w,'void idWeapon::Event_AnimDone( int channel, int blendFrames )\n{\n','''void idWeapon::Event_AnimDone( int channel, int blendFrames )
{
    if(!common->IsMultiplayer() && channel==ANIMCHANNEL_ALL && WEAPON_ATTACK &&
       idStr::Cmp(spawnArgs.GetString("model_view"),"viewmodel_reach_m37")==0)
    {
        const idAnimBlend* recovery=animator.CurrentAnim(ANIMCHANNEL_ALL);
        const char* name=recovery!=NULL ? recovery->AnimFullName() : "";
        const bool full=idStr::Cmp(name,"reload_full")==0;
        const bool empty=idStr::Cmp(name,"reload_empty")==0;
        const int ready=full ? 3067 : 3767;
        if((full || empty) && recovery->AnimTime(gameLocal.time)>=ready)
        {idThread::ReturnInt(true);return;}
    }
''',f)
 changed[f]=w;return changed
