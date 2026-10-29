// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_WEAPON_PROJECTION_H
#define REACH_WEAPON_PROJECTION_H

#include <cmath>

namespace ReachProjection
{

inline bool ModelNamed( const char* model, const char* expected )
{
	// Doom's precompiled headers redefine strcmp, including qualified uses.
	while( *model != '\0' && *model == *expected )
	{
		++model;
		++expected;
	}
	return *model == *expected;
}

inline bool Eligible( const char* model, bool tagged, bool depthHack,
	int allowedView, int currentView, bool subview, bool mirror )
{
	if( model == nullptr || !tagged || !depthHack || allowedView <= 0 ||
		allowedView != currentView || subview || mirror )
	{
		return false;
	}
	return ModelNamed( model, "models/md5/weapons/reach_ar/view.md5mesh" ) ||
		ModelNamed( model, "models/md5/weapons/reach_ar/view_appearance_r15.md5mesh" ) ||
        ModelNamed( model, "models/md5/weapons/reach_magnum/view.md5mesh" ) ||
        ModelNamed( model, "reach_magnum_flash.prt" ) ||
        ModelNamed( model, "models/md5/weapons/reach_shotgun/view.md5mesh" ) ||
        ModelNamed( model, "reach_shotgun_flash.prt" ) ||
        ModelNamed( model, "models/md5/weapons/reach_plasma_repeater/view.md5mesh" ) ||
        ModelNamed( model, "reach_plasma_repeater_flash.prt" ) ||
		ModelNamed( model, "reach_ar_flash.prt" ) || ModelNamed( model, "reach_ar_flash_r15.prt" ) ||
        ModelNamed( model, "reach_ar_brake_native.prt" );
}

// The reference is horizontal FOV at 4:3, matching Source's weapon convention.
// This is an authoring control, not a recovered Reach retail camera constant.
// Change only focal lengths: retain the host's jitter, clipping and depth rows.
inline bool Apply( float* projection, float horizontalFov4By3, float aspect )
{
	if( projection == nullptr || !std::isfinite( horizontalFov4By3 ) ||
		!std::isfinite( aspect ) || horizontalFov4By3 < 1.0f ||
		horizontalFov4By3 > 175.0f || aspect < 0.1f || aspect > 10.0f )
	{
		return false;
	}
	if( !std::isfinite( projection[0] ) || !std::isfinite( projection[5] ) ||
		projection[0] == 0.0f || projection[5] == 0.0f )
	{
		return false;
	}

	constexpr double degreesToRadians = 0.017453292519943295769;
	const double verticalHalfTangent =
		std::tan( horizontalFov4By3 * degreesToRadians * 0.5 ) * 0.75;
	const float horizontalFocal = static_cast<float>( 1.0 / ( aspect * verticalHalfTangent ) );
	const float verticalFocal = static_cast<float>( 1.0 / verticalHalfTangent );
	if( !std::isfinite( horizontalFocal ) || !std::isfinite( verticalFocal ) )
	{
		return false;
	}

	projection[0] = std::copysign( horizontalFocal, projection[0] );
	projection[5] = std::copysign( verticalFocal, projection[5] );
	return true;
}

} // namespace ReachProjection

#endif


