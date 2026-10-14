// SPDX-License-Identifier: GPL-3.0-or-later
// Reproduce the actual Doom Str.h restriction around the standalone helper.
#define strcmp DOOM_REQUIRES_IDSTR_CMP
#include "WeaponProjection.h"
#undef strcmp
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>

namespace
{
using Matrix = std::array<float, 16>;

void Require( bool condition, const char* message )
{
	if( !condition )
	{
		std::fprintf( stderr, "Projection check failed: %s\n", message );
		std::exit( 1 );
	}
}

bool Close( double a, double b )
{
	return std::abs( a - b ) < 2.0e-6;
}

Matrix HostProjection()
{
	// Nonzero offsets model an asymmetric, jittered perspective camera.
	return { 1.2f, 0.0f, 0.004f, 0.0f,
			 0.0f, -2.1f, -0.003f, 0.0f,
			 0.0f, 0.0f, -1.0002f, -0.20002f,
			 0.0f, 0.0f, -1.0f, 0.0f };
}

void CheckCamera( float aspect, double horizontalFov )
{
	Matrix projection = HostProjection();
	const Matrix original = projection;
	Require( ReachProjection::Apply( projection.data(), 54.0f, aspect ), "valid FOV rejected" );
	for( int i = 0; i < 16; ++i )
	{
		if( i != 0 && i != 5 )
		{
			Require( std::memcmp( &projection[i], &original[i], sizeof( float ) ) == 0,
				"jitter, clipping or depth term changed" );
		}
	}
	Require( projection[0] > 0.0f && projection[5] < 0.0f, "host axis signs changed" );

	// Independently specified screen-edge ray angles from the Source convention.
	// The same vertical edge must hold at standard widescreen and ultrawide.
	constexpr double radians = 0.017453292519943295769;
	const double horizontalRay = std::tan( horizontalFov * radians * 0.5 );
	const double verticalRay = std::tan( 41.82812169855287 * radians * 0.5 );
	Require( Close( projection[0] * horizontalRay, 1.0 ), "horizontal edge ray maps incorrectly" );
	Require( Close( -projection[5] * verticalRay, 1.0 ), "vertical edge ray maps incorrectly" );

	// Project the same camera ray at two distances, including original jitter.
	for( double distance : { 1.0, 100.0 } )
	{
		const double x = ( projection[0] * horizontalRay * distance - projection[2] * distance ) / distance;
		const double y = ( projection[5] * verticalRay * distance - projection[6] * distance ) / distance;
		Require( Close( x, 1.0 - original[2] ), "horizontal jitter changed with depth" );
		Require( Close( y, -1.0 - original[6] ), "vertical jitter changed with depth" );
	}
}

void CheckInvalidInputs()
{
	const float nan = std::numeric_limits<float>::quiet_NaN();
	const float infinity = std::numeric_limits<float>::infinity();
	for( float fov : { 0.0f, -10.0f, 0.5f, 176.0f, nan, infinity } )
	{
		Matrix projection = HostProjection();
		const Matrix original = projection;
		Require( !ReachProjection::Apply( projection.data(), fov, 16.0f / 9.0f ), "invalid FOV accepted" );
		Require( std::memcmp( projection.data(), original.data(), sizeof( Matrix ) ) == 0,
			"invalid FOV modified host projection" );
	}
	for( float aspect : { 0.0f, -1.0f, 0.01f, 20.0f, nan, infinity } )
	{
		Matrix projection = HostProjection();
		const Matrix original = projection;
		Require( !ReachProjection::Apply( projection.data(), 54.0f, aspect ), "invalid aspect accepted" );
		Require( std::memcmp( projection.data(), original.data(), sizeof( Matrix ) ) == 0,
			"invalid aspect modified host projection" );
	}
	for( int index : { 0, 5 } )
	{
		Matrix projection = HostProjection();
		projection[index] = 0.0f;
		const Matrix original = projection;
		Require( !ReachProjection::Apply( projection.data(), 54.0f, 16.0f / 9.0f ), "non-perspective focal accepted" );
		Require( std::memcmp( projection.data(), original.data(), sizeof( Matrix ) ) == 0,
			"rejected host projection modified" );
	}
	Require( !ReachProjection::Apply( nullptr, 54.0f, 16.0f / 9.0f ), "null matrix accepted" );
}

void CheckScope()
{
	const char* rifle = "models/md5/weapons/reach_ar/view.md5mesh";
	Require( ReachProjection::Eligible( rifle, true, true, 1, 1, false, false ), "owned rifle rejected" );
	Require( ReachProjection::Eligible( "reach_ar_flash.prt", true, true, 1, 1, false, false ), "owned flash rejected" );
	Require( !ReachProjection::Eligible( "models/md5/weapons/machinegun/view.md5mesh", true, true, 1, 1, false, false ), "stock weapon modified" );
	Require( !ReachProjection::Eligible( rifle, false, true, 1, 1, false, false ), "untagged rifle modified" );
	Require( !ReachProjection::Eligible( rifle, true, false, 1, 1, false, false ), "world model modified" );
	Require( !ReachProjection::Eligible( rifle, true, true, 0, 0, false, false ), "unrestricted world entity modified" );
	Require( !ReachProjection::Eligible( rifle, true, true, 1, 2, false, false ), "another player's view modified" );
	Require( !ReachProjection::Eligible( rifle, true, true, 1, 1, true, false ), "subview modified" );
	Require( !ReachProjection::Eligible( rifle, true, true, 1, 1, false, true ), "mirror modified" );
	Require( !ReachProjection::Eligible( nullptr, true, true, 1, 1, false, false ), "null model modified" );
}
} // namespace

int main()
{
	CheckCamera( 4.0f / 3.0f, 54.0 );
	CheckCamera( 16.0f / 9.0f, 68.38180955042496 );
	CheckCamera( 3440.0f / 1440.0f, 84.78589368943273 );
	CheckInvalidInputs();
	CheckScope();
	std::puts( "Weapon projection: reference rays, aspect, jitter, depth, signs, invalid inputs and first-person scope passed." );
	return 0;
}
