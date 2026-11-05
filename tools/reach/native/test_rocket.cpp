#include <cassert>
#include <cmath>
#include "CameraMotion.h"
#include "WeaponProjection.h"
int main() {
    const auto start=ReachCamera::RocketReloadMotion(0);
    const auto end=ReachCamera::RocketReloadMotion(115.0f/30);
    float peak=0;
    for(int axis=0;axis<3;++axis) {
        assert(std::fabs(start.a[axis])<.0001f && std::fabs(end.a[axis])<.0001f);
        assert(std::fabs(start.p[axis])<.0001f && std::fabs(end.p[axis])<.0001f);
    }
    for(int tick=0;tick<3840;++tick) {
        const auto m=ReachCamera::RocketReloadMotion(float(tick)*.001f);
        const auto n=ReachCamera::RocketReloadMotion(float(tick+1)*.001f);
        for(int axis=0;axis<3;++axis) {
            assert(std::isfinite(m.a[axis]) && std::fabs(n.a[axis]-m.a[axis])<.025f);
            if(std::fabs(m.a[axis])>peak) peak=std::fabs(m.a[axis]);
        }
    }
    assert(peak>.7f && peak<1.4f);
    assert(ReachProjection::Eligible("models/md5/weapons/reach_rocket/view.md5mesh",true,true,1,1,false,false));
    assert(!ReachProjection::Eligible("models/reach/rocket/held.md5mesh",true,true,1,1,false,false));
    assert(!ReachProjection::Eligible("models/md5/weapons/reach_rocket/view.md5mesh",true,true,1,1,false,true));
}
