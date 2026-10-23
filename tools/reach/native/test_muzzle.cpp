// SPDX-License-Identifier: GPL-3.0-or-later
#include "MuzzleEffects.h"
#include <cassert>
#include <cmath>
#include <limits>
#include <initializer_list>
int main()
{
    for( int previous = 0; previous < 8; ++previous )
    {
        bool seen[8] = {};
        for( int random = 0; random < 7; ++random )
        {
            const int next = ReachMuzzle::NextVariant( previous, random );
            assert( next >= 0 && next < 8 && next != previous && !seen[next] );
            seen[next] = true;
        }
    }
    for( float weapon : { 35.0f, 54.0f, 90.0f } )
    {
        for( float world : { 40.0f, 60.0f, 90.0f } )
        {
            const double rad = 0.017453292519943295769;
            const double pWeapon = 1.0 / ( std::tan( weapon * rad * .5 ) * .75 );
            const double pWorld = 1.0 / std::tan( world * rad * .5 );
            const float scale = ReachMuzzle::WorldSmokeScale( weapon, world );
            // The same point projects to the same vertical screen coordinate.
            assert( std::abs( pWorld * ( -3.0 * scale ) / 40 - pWeapon * -3 / 40 ) < 1e-6 );
        }
    }
    assert( ReachMuzzle::WorldSmokeScale( 0, 60 ) == 1 );
    assert( ReachMuzzle::WorldSmokeScale( 54, std::numeric_limits<float>::quiet_NaN() ) == 1 );
}
