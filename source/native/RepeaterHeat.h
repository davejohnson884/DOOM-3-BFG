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
// Reach function-overlay scalar bounds .5..1; source chase times .25/2.5 s.
// The authored barrel_spin clip supplies the rotation, not per-shot restarts.
inline float MotorTarget(float heat,bool firing,bool venting,bool energy) {
 if(venting) {return 1.0f;}
 return firing && energy ? .5f+.5f*(Rate(heat)-3.0f)/12.0f : 0.0f;
}
inline float ChaseMotor(float speed,float target,float seconds) {
 speed=Clamp(speed);target=Clamp(target);if(seconds<=0) {return speed;}
 const float amount=seconds/(target>speed?.25f:2.5f);
 return target>speed ? (speed+amount<target?speed+amount:target) : (speed-amount>target?speed-amount:target);
}
inline float MotorPhase(float phase,float before,float after,float seconds,float clipSeconds) {
 if(seconds<=0 || clipSeconds<=0) {return phase;}
 const float value=phase+.5f*(before+after)*seconds/clipSeconds;
 return value-std::floor(value);
}
}
#endif
