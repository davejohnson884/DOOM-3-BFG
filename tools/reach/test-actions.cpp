#include "../../neo/d3xp/ReachAction.h"
#include <cstdio>
#include <cstdlib>

static void Check( bool ok, const char *message ) {
	if ( !ok ) { std::fprintf( stderr, "FAIL: %s\n", message ); std::exit( 1 ); }
}
int main() {
	reachAction_t action;
	Check( action.Begin( REACH_ACTION_GRENADE, 100, 250, 450 ), "grenade accepted while idle" );
	Check( !action.Begin( REACH_ACTION_MELEE, 110, 100, 500 ), "melee cannot overlap grenade windup" );
	Check( action.ConsumeEffect( 349 ) == REACH_ACTION_NONE, "windup does not consume grenade ammo" );
	Check( action.ConsumeEffect( 350 ) == REACH_ACTION_GRENADE, "throw becomes due at the windup boundary" );
	Check( action.ConsumeEffect( 351 ) == REACH_ACTION_NONE, "throw effect cannot repeat next frame" );
	Check( action.BlocksWeapon( 799 ) && !action.BlocksWeapon( 800 ), "fire waits until recovery ends" );
	Check( action.Begin( REACH_ACTION_MELEE, 800, 100, 500 ), "melee can start after grenade recovery" );
	action.CancelPending();
	Check( action.ConsumeEffect( 1000 ) == REACH_ACTION_NONE, "weapon switch or cinematic cancels pending damage" );
	Check( !action.Begin( REACH_ACTION_MELEE, 1000, 100, 500 ), "cancelling cannot bypass the shared cooldown" );
	action.Reset();
	Check( !action.BlocksWeapon( 0 ), "spawn/load resets old action times" );
	Check( action.Begin( REACH_ACTION_GRENADE, 0, 250, 450 ), "new action after reset" );
	Check( !action.Begin( REACH_ACTION_MELEE, 5000, 100, 500 ), "frame hitch cannot overwrite an unconsumed throw" );
	Check( action.ConsumeEffect( 5000 ) == REACH_ACTION_GRENADE, "accepted action resolves once after a long frame" );
	Check( action.ConsumeEffect( 5001 ) == REACH_ACTION_NONE, "late resolution still has no duplicate effect" );
	Check( action.Begin( REACH_ACTION_MELEE, 5001, 0, 0 ), "zero-time prototype settings are supported" );
	Check( action.ConsumeEffect( 5001 ) == REACH_ACTION_MELEE, "zero windup resolves immediately" );
	std::puts( "PASS: quick action timing, mutual exclusion, cancellation and long-frame scenarios" );
	return 0;
}
