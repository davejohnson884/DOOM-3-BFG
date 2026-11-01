// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_M319_POLICY_H
#define REACH_M319_POLICY_H
namespace ReachM319 {
enum Latch { Holding=0, Normal=1, Armed=2, Remote=3 };
inline int Step(int mode,bool held,int age,bool bounced) {
 if(mode==Normal || mode==Remote) return mode;
 if(mode==Holding && held && (age>=300 || bounced)) mode=Armed;
 if(!held) return mode==Armed ? Remote : Normal;
 return mode;
}
inline bool DirectImpact(bool tethered,bool actor,float speed,float incidence) {
 return !tethered && ((actor && speed>=600.0f) || (!actor && speed>=900.0f && speed<=1680.0f && incidence>=.9659258f));
}
inline float FlightSpeed(float distance) {
 const float fraction=distance<=120.0f ? 0.0f : distance>=1200.0f ? 1.0f : (distance-120.0f)/1080.0f;
 return 1450.0f-100.0f*fraction;
}
inline int RemainingFuse(int now,int bounce) {int d=bounce+500-now;return d>0?d:0;}
}
#endif
