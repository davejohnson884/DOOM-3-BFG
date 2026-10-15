#include "ReachQuickActions.h"
#include <cassert>
#include <iostream>
int main()
{
	using namespace ReachQuickActions;
	assert( Read( 10, 9, 23 ) == 1 );
	assert( Read( 10, 9, 24 ) == 2 );
	assert( Read( 10, 10, 23 ) == 0 );
	assert( Read( 10, 10, 24 ) == 0 );
	assert( Read( 0, 255, 23 ) == 1 );
	assert( Read( 0, 255, 24 ) == 2 );
	assert( Read( 20, 19, 4 ) == 0 ); // ordinary weapon selection
	assert( Read( 20, 19, 13 ) == 0 ); // reload
	assert( BounceFuseDelay( 100, 0, 1400, 600 ) == 1300 );
	assert( BounceFuseDelay( 900, 0, 1400, 600 ) == 600 );
	assert( BounceFuseDelay( 2500, 0, 1400, 650 ) == 650 );
	assert( BounceFuseDelay( 7000, 6000, 1400, 650 ) == 650 );
	std::cout << "PASS: native impulse edges, byte sequence wrap, ordinary inputs and first-floor arming/timer deadlines\n";
}
