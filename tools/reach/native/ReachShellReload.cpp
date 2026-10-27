// Source-driven shell reload adapter for the unchanged Reach weapon script.
// State uses the weapon's existing saved spawnArgs; no save format changes.
bool idWeapon::ReachShellReload( int channel )
{
    if( common->IsMultiplayer() || !ReachCombatWeapon(spawnArgs) ||
        !spawnArgs.GetBool("reach_shell_reload") || channel!=ANIMCHANNEL_ALL ) {return false;}
    int phase=spawnArgs.GetInt("_reach_shellPhase");
    if( phase==0 ) {return false;}
    if( owner==NULL || owner->health<=0 ) {spawnArgs.SetInt("_reach_shellPhase",0);return false;}
    if( phase==2 && !spawnArgs.GetBool("_reach_shellCommitted") &&
        gameLocal.time>=spawnArgs.GetInt("_reach_shellCommitTime") )
    {
        spawnArgs.SetBool("_reach_insertingShell",true);
        Event_AddToClip(1);
        spawnArgs.SetBool("_reach_insertingShell",false);
        spawnArgs.SetBool("_reach_shellCommitted",true);
        if( cvarSystem->GetCVarBool("g_debugWeapon") )
            gameLocal.Printf("[ReachShell] inserted clip=%d reserve=%d\n",ammoClip.Get(),owner->inventory.HasAmmo(ammoType,ammoRequired));
    }
    if( gameLocal.time<animDoneTime ) {idThread::ReturnInt(false);return true;}
    const bool interrupt=spawnArgs.GetBool("_reach_shellInterrupt") && ammoClip.Get()>0;
    const bool canLoad=ammoClip.Get()<clipSize && owner->inventory.HasAmmo(ammoType,ammoRequired)!=0;
    const char* next=NULL;
    if( phase!=3 && canLoad && !interrupt )
    {
        phase=2;next="reload_shell";
        spawnArgs.SetBool("_reach_shellCommitted",false);
        spawnArgs.SetInt("_reach_shellCommitTime",gameLocal.time+spawnArgs.GetInt("reach_shell_commit_ms","433"));
    }
    else if( phase!=3 && spawnArgs.GetBool("_reach_shellStartedEmpty") && ammoClip.Get()>0 )
    {
        phase=3;next="reload_chamber";
    }
    if( next!=NULL )
    {
        const int anim=animator.GetAnim(next);
        if( anim==0 ) {gameLocal.Error("Reach shotgun missing reload animation %s",next);return false;}
        animator.PlayAnim(channel,anim,gameLocal.time,FRAME2MS(2));
        animDoneTime=animator.CurrentAnim(channel)->GetEndTime();
        spawnArgs.SetInt("_reach_shellPhase",phase);
        idThread::ReturnInt(false);return true;
    }
    spawnArgs.SetInt("_reach_shellPhase",0);
    spawnArgs.SetBool("_reach_shellFireQueued",interrupt);
    idThread::ReturnInt(true);return true;
}
