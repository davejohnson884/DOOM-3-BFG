#include "../../neo/d3xp/ReachSprint.h"
#include <cstdio>
#include <cstdlib>

static void Check( bool condition, const char *message ) {
	if ( !condition ) { std::fprintf( stderr, "FAIL: %s\n", message ); std::exit( 1 ); }
}

int main() {
	reachSprint_t sprint;
	Check( !sprint.BlocksWeapon( 0 ), "stock start permits firing" );
	Check( !sprint.HasCharge( 1.0f, 7.0f, 0.25f ), "nearly empty charge cannot restart sprint" );
	sprint.Update( true, sprint.HasCharge( 7.0f, 7.0f, 0.25f ), 100, 180 );
	Check( sprint.IsActive() && sprint.BlocksWeapon( 100 ), "sprinting locks firing" );
	Check( sprint.HasCharge( 0.1f, 7.0f, 0.25f ), "running can consume charge below the start threshold" );
	sprint.Update( false, true, 200, 180 );
	Check( !sprint.IsActive() && sprint.BlocksWeapon( 379 ), "attack interruption retains recovery lock" );
	sprint.Update( true, true, 300, 180 );
	Check( !sprint.IsActive(), "holding sprint cannot bypass recovery" );
	sprint.Update( false, true, 350, 180 );
	Check( !sprint.BlocksWeapon( 380 ), "releasing sprint again does not extend recovery" );
	sprint.Update( true, true, 400, 180 );
	sprint.Update( true, sprint.HasCharge( 0.0f, 7.0f, 0.25f ), 500, 180 );
	Check( !sprint.IsActive() && sprint.BlocksWeapon( 500 ), "exhaustion ends sprint with recovery" );
	sprint.Update( true, false, 900, 180 );
	Check( !sprint.IsActive() && !sprint.BlocksWeapon( 900 ), "reload/cinematic/airborne veto prevents sprint" );
	sprint.Update( true, true, 1000, 180 );
	sprint.Reset();
	Check( !sprint.IsActive() && !sprint.BlocksWeapon( 0 ), "save restore clears old-world action timestamps" );
	Check( sprint.HasCharge( 0.0f, 0.0f, 0.25f ), "maps disabling stamina permit unlimited sprint" );
	sprint.Update( true, true, 0, 0 );
	sprint.Stop( 10, 0 );
	Check( !sprint.BlocksWeapon( 10 ), "zero recovery remains supported" );
	std::puts( "PASS: sprint action, charge, recovery and reset scenarios" );
	return 0;
}
