#include "CameraMotion.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
int main()
{
    using namespace ReachCamera;
    for( int p=Reload;p<=SprintExit;++p )
    {
        if( p==SprintLoop ) {continue;}
        for( float t : {0.0f,1.0f} )
        {
            Motion m=ProfileMotion(static_cast<Profile>(p),t);
            for(int i=0;i<3;++i) {assert(m.p[i]==0 && m.a[i]==0);}
        }
    }
    assert(ShotPulse(-1)==0 && ShotPulse(0)==0 && ShotPulse(165)==0 && ShotPulse(999)==0);
    assert(ShotPulse(18)>.99f);
    State fast,slow;Motion target;target.a[0]=1;
    fast.Evaluate(0,target);slow.Evaluate(0,target);
    Motion a,b;
    for(int t=10;t<=1000;t+=10) {a=fast.Evaluate(t,target);}
    for(int t=40;t<=1000;t+=40) {b=slow.Evaluate(t,target);}
    assert(std::fabs(a.a[0]-b.a[0])<.00001f);
    // A second query in the same simulation frame must be idempotent.
    Motion twice=fast.Evaluate(1000,target);assert(twice.a[0]==a.a[0]);
    // Interrupted actions return to neutral; no permanent mouse/aim delta.
    target=Motion();for(int t=1010;t<=1700;t+=10) {a=fast.Evaluate(t,target);}
    for(int i=0;i<3;++i) {assert(a.p[i]==0 && a.a[i]==0);}
    State burst;burst.Evaluate(1000,target);
    for(int t=1000;t<=2000;t+=100) {burst.Shot(t);a=burst.Evaluate(t+18,target);assert(std::fabs(a.a[0])<1.5f);}
    a=burst.Evaluate(2400,target);assert(a.a[0]==0 && a.a[1]==0 && a.a[2]==0);
    // Clock rewind and Clear reset all transient action/shot state.
    burst.Shot(2500);burst.Evaluate(2500,target);
    a=burst.Evaluate(50,target);assert(burst.sequence==0 && a.a[0]==0);
    target.p[0]=target.p[1]=target.p[2]=100;target.a[0]=100;
    for(int t=60;t<200;t+=10) {a=burst.Evaluate(t,target);}
    assert(a.a[0]<=3.5f);assert(a.p[0]*a.p[0]+a.p[1]*a.p[1]+a.p[2]*a.p[2]<4.00001f);
    std::puts("PASS camera recovery, duplicate-query safety, rate independence, shot settling and bounds");
}

