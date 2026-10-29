// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_REPEATER_HEAT_H
#define REACH_REPEATER_HEAT_H
#include <cmath>
namespace ReachRepeater {
inline float Clamp(float v) {return v<0?0:(v>1?1:v);}
// Owned forge_halo tag: 15 -> 3 rounds/s; exponent mapping payload (0,1,1.5).
inline float Rate(float heat) {return 15.0f-12.0f*std::pow(Clamp(heat),1.5f);}
// Scalar bounds of exported heat_loss: .06 .. .25. The source multispline's
// normalized cubic is reconstructed here; this is a host curve approximation.
inline float PassiveRate(float heat) {
 const float h=Clamp(heat);const float curve=Clamp(((.4867532f*h+.0264935f)*h-1.5132467f)*h+1.0f);
 return .06f+.19f*curve;
}
inline float Cool(float heat,float seconds,bool venting,bool firing) {
 float h=Clamp(heat);if(seconds<=0 || firing) {return h;}
 if(venting) {return Clamp(h-seconds/2.5f);}
 // Bounded integration is independent of render frame rate, including holster.
 float left=seconds>30?30:seconds;
 while(left>0 && h>0) {const float dt=left>.004166667f?.004166667f:left;h=Clamp(h-dt*PassiveRate(h));left-=dt;}
 return h;
}
inline float Shot(float heat) {return Clamp(heat+.03f);}
}
#endif
