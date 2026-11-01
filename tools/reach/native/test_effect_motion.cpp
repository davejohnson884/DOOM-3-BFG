#include "ReachEffectMotion.h"
#include <cassert>
#include <cmath>
#include <initializer_list>
int main() {
    using namespace ReachEffectMotion;
    assert(Travel(0,3)==0 && AccelerationTravel(0,3)==0);
    assert(Travel(2,0)==2 && AccelerationTravel(2,0)==2);
    // Integrate the physical differential equations independently at a small
    // timestep and compare the closed-form path over several lifetimes.
    for(float drag: {0.0f,1.5f,3.0f,4.0f}) {
        double p=0,v=150,dt=0.00001;
        for(int n=0;n<100000;n++){p+=v*dt;v+=(12-drag*v)*dt;}
        const float analytic=150*Travel(1,drag)+12*AccelerationTravel(1,drag);
        assert(std::abs(p-analytic)<0.005);
        assert(Travel(.5f,drag)<Travel(1,drag));
    }
    assert(std::abs(Travel(1,.00001f)-1)<.0001f);
}
