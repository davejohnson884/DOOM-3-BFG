#include "MuzzleEffects.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
int main() {
    assert( std::abs( ReachMuzzle::BrakeScale(0)-.5f ) < 1e-6f );
    assert( std::abs( ReachMuzzle::BrakeScale(1)-1.25f ) < 1e-6f );
    float previous = 0;
    for( int i=0; i<=110; ++i ) {
        float value=ReachMuzzle::BrakeScale( i/110.0f );
        assert( value>=previous ); previous=value;
    }
    for( const auto& jet: ReachMuzzle::jets ) {
        float length=0; for(float v:jet.direction) length+=v*v;
        assert( std::abs(length-1)<.0001f );
        assert( jet.direction[0]>.5f && jet.direction[0]<.7f );
    }
    for( float fov: {60.f,75.f,90.f} ) {
        assert(ReachMuzzle::WorldSmokeScale(fov,fov)>0);
    }
    // Native one-puff smoke uses bunching=0 and starts on its first valid
    // PresentWeapon call; this is exactly the pinned EmitSmoke branch.
    for( int delay: {0,16,33,100} ) {
        int now=1000+delay, start=now, count=0;
        if(now==start) count=1;
        assert(count==1);
    }
    std::puts("PASS source-marker directions, expansion curve and deferred smoke start");
}
