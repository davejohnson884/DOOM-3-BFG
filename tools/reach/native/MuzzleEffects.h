// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_MUZZLE_EFFECTS_H
#define REACH_MUZZLE_EFFECTS_H
#include <cmath>
namespace ReachMuzzle
{
// Convert a weapon-projected point to the same screen position in world FOV.
// Forward distance is retained; only view-space lateral/vertical offsets scale.
inline float WorldSmokeScale( float weaponHorizontal4By3, float worldVertical )
{
    if( !std::isfinite( weaponHorizontal4By3 ) || !std::isfinite( worldVertical ) ||
        weaponHorizontal4By3 < 1 || weaponHorizontal4By3 > 175 ||
        worldVertical < 1 || worldVertical > 175 ) { return 1.0f; }
    constexpr double radians = 0.017453292519943295769;
    return static_cast<float>( std::tan( worldVertical * radians * .5 ) /
        ( std::tan( weaponHorizontal4By3 * radians * .5 ) * .75 ) );
}
// Uniform among the other seven variants; no immediate repetition or new state.
inline int NextVariant( int previous, int randomSeven )
{
    previous = previous >= 0 && previous < 8 ? previous : 0;
    int choice = randomSeven % 7;
    if( choice < 0 ) { choice += 7; }
    return choice >= previous ? choice + 1 : choice;
}
}
#endif
