// SPDX-License-Identifier: GPL-3.0-or-later
#include "ReachM37Handling.h"
#include "CameraMotion.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>
int main() {
    using namespace ReachLMG;
    // Real automatic intervals must build bloom, not clear it between shots.
    float bloom=0;float first=0,last=0;
    for(int shot=0;shot<90;++shot) {
        bloom=Bloom(bloom,shot==0 ? -1 : 66);
        const float spread=Spread(bloom,0,false,true);
        if(shot==0) {first=spread;}last=spread;bloom=Clamp(bloom+.045f,0,1);
    }
    assert(first>.15f && first<.17f && last>.61f && last<.63f);
    assert(Bloom(bloom,66)==1 && Bloom(bloom,790)==0);
    assert(Spread(1,1,false,true)>Spread(1,0,false,true)*3);
    assert(Spread(1,0,true,true)<Spread(1,0,false,true)*.65f);
    assert(Spread(1,1,false,false)>Spread(1,1,false,true)+1.7f);
    assert(AimKick(true,false,0)>AimKick(false,false,0));
    assert(AimKick(false,true,0)<AimKick(false,false,0));
    assert(Spread(0,0,false,true)==first);
    // Same movement envelope at 30/60/120 Hz; rapid raise and slower settling.
    float reference=0;
    for(int step:{8,16,32}) {
        float motion=0;
        for(int t=0;t<960;t+=step) {motion=Movement(motion,1,float(step)*.001f);}
        assert(motion>.999f);
        for(int t=0;t<192;t+=step) {motion=Movement(motion,0,float(step)*.001f);}
        if(step==8) {reference=motion;} else {assert(std::fabs(motion-reference)<.00001f);}
        assert(motion>.33f && motion<.35f);
    }
    // Continuous LMG fire stays bounded, distinct from the pump-shotgun kick,
    // then clears completely without a held recovery frame or aim mutation.
    for(int step:{8,16,32}) {
        ReachCamera::State state;int shot=0;float peak=0;
        for(int now=0;now<10000;now+=step) {
            if(now<6000 && now>=shot*66) {state.Shot(now);++shot;}
            const auto m=state.M37Shot(now);const auto duplicate=state.M37Shot(now);
            for(int i=0;i<3;++i) {
                assert(m.a[i]==duplicate.a[i] && m.p[i]==duplicate.p[i]);
                assert(std::isfinite(m.a[i]) && std::fabs(m.a[i])<1);
                assert(std::fabs(m.p[i])<.25f);
                if(now>6300) {assert(m.a[i]==0 && m.p[i]==0);}
            }
            peak=std::fmax(peak,-m.a[0]);
        }
        assert(peak>.35f && peak<.7f);
    }
    std::puts("PASS M37 bloom, stance, motion settling, recoil control, sustained camera bounds and full recovery");
}
