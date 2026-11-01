#ifndef REACH_EFFECT_MOTION_H
#define REACH_EFFECT_MOTION_H
#include <cmath>
// Opt-in visual trajectory only. No entity, damage, physics or archive fields.
namespace ReachEffectMotion {
inline float Travel(float time, float drag) {
    if(time<=0.0f) return 0.0f;
    if(drag<0.0001f) return time;
    return -std::expm1(-drag*time)/drag;
}
inline float AccelerationTravel(float time, float drag) {
    if(time<=0.0f) return 0.0f;
    if(drag<0.0001f) return 0.5f*time*time;
    return (time-Travel(time,drag))/drag;
}
}
#endif
