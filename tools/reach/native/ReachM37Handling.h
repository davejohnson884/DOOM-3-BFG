// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_M37_HANDLING_H
#define REACH_M37_HANDLING_H
#include <cmath>
namespace ReachLMG {
inline float Clamp(float x,float low,float high) {return x<low ? low : (x>high ? high : x);}
inline float Movement(float previous,float current,float seconds) {
    current=Clamp(current,0,1);previous=Clamp(previous,0,1);
    if(seconds<=0) {return previous;}
    const float response=current>previous ? .06f : .18f;
    const float value=current+(previous-current)*std::exp(-seconds/response);
    return value<.001f && current==0 ? 0 : value;
}
// Decay begins after a pause, rather than erasing the increment between shots.
inline float Bloom(float previous,int elapsedMs,int holdMs=140,float recovery=.65f) {
    if(elapsedMs<0) {return 0;}
    const float elapsed=elapsedMs>holdMs ? float(elapsedMs-holdMs)*.001f : 0;
    return Clamp(previous-elapsed/(recovery>.01f ? recovery : .01f),0,1);
}
inline float Spread(float bloom,float movement,bool crouched,bool grounded,
                    float base=.16f,float sustained=.46f,float moving=1.45f,float airborne=1.8f) {
    const float cone=base+sustained*Clamp(bloom,0,1)+moving*Clamp(movement,0,1);
    return Clamp(cone*(crouched ? .64f : 1)+(grounded ? 0 : airborne),.05f,6);
}
inline float AimKick(bool first,bool crouched,float movement,float gain=1) {
    return (first ? .27f : .17f)*(crouched ? .68f : 1)*(1+.15f*Clamp(movement,0,1))*Clamp(gain,0,2);
}
}
#endif
