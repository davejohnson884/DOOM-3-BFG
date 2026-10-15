// Reach opt-in weapon projection / ordinary SP gameplay commands, no cheat flag.
static void ReachQueueInputCommand( int action )
{
	idPlayer* player = gameLocal.GetLocalPlayer();
	if( player == NULL || !player->weapon.IsValid() ) { return; }
	if( !player->weapon.GetEntity()->ReachQueueAction( action ) && g_debugWeapon.GetBool() )
	{
		gameLocal.Printf( "[ReachInput r15] action ignored: active weapon is not the Reach AR or player cannot act\n" );
	}
}
static void Cmd_ReachMelee_f( const idCmdArgs& args )
{
	( void )args;
	ReachQueueInputCommand( 1 );
}
static void Cmd_ReachGrenade_f( const idCmdArgs& args )
{
	( void )args;
	ReachQueueInputCommand( 2 );
}

