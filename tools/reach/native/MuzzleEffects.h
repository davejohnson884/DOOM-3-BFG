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
// Original rifle muzzle_flash marker positions relative to primary_trigger.
struct Jet { float offset[3]; float direction[3]; };
static const Jet jets[5] = {
    { { -0.670954585f, -2.28881831e-06f, -0.393943638f }, { 0.573576186f, 0.0f, -0.819152211f } },
    { { -0.670954585f, 0.369433586f, -0.125531405f }, { 0.57357614f, 0.779060168f, -0.253131792f } },
    { { -0.670954585f, -0.228327944f, 0.308767855f }, { 0.573576086f, -0.481485207f, 0.662708489f } },
    { { -0.670954585f, -0.36728896f, -0.13196066f }, { 0.573576508f, -0.774523715f, -0.266689003f } },
    { { -0.670954585f, 0.228321075f, 0.308767855f }, { 0.573576306f, 0.481485578f, 0.662707977f } }
};
inline float BrakeScale( float age ) {
    age = age < 0 ? 0 : ( age > 1 ? 1 : age );
    return .5f + .75f * ( ( -.148148179f * age - .703703642f ) * age + 1.851851821f ) * age;
}
}
#endif
