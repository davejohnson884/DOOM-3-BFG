#include "CameraMotion.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
int main()
{
    using namespace ReachCamera;
    for( int p=Reload;p<=Throw;++p )
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
    assert(a.a[0]<=6.0f);assert(a.p[0]*a.p[0]+a.p[1]*a.p[1]+a.p[2]*a.p[2]<4.00001f);
    // Stronger shot pulse is proportional, finite and still has no residual.
    State original, stronger;Motion neutral;
    original.Evaluate(1000,neutral);stronger.Evaluate(1000,neutral);
    original.Shot(1000);stronger.Shot(1000);
    Motion baseShot=original.Evaluate(1018,neutral);
    Motion strongShot=stronger.Evaluate(1018,neutral,2.5f);
    assert(std::fabs(strongShot.a[0]-2.5f*baseShot.a[0])<.00001f);
    for(int t=1100;t<=2000;t+=100) {stronger.Shot(t);a=stronger.Evaluate(t+18,neutral,2.5f);assert(std::fabs(a.a[0])<3.75f);}
    a=stronger.Evaluate(2400,neutral,2.5f);
    for(int i=0;i<3;++i) {assert(a.p[i]==0 && a.a[i]==0);}
    // Action scaling affects every axis; accepted ready profile stays exact.
    Motion reload=ProfileMotion(Reload,.4f), scaled=ScaleMotion(reload,2.5f);
    for(int i=0;i<3;++i) {assert(scaled.p[i]==reload.p[i]*2.5f && scaled.a[i]==reload.a[i]*2.5f);}
    for(float t:{0.0f,.25f,.5f,.75f,1.0f}) {
        Motion ready=ProfileMotion(Raise,t),same=ScaleMotion(ready,1);
        for(int i=0;i<3;++i) {assert(ready.p[i]==same.p[i] && ready.a[i]==same.a[i]);}
    }
    // Distinct source-timed removal, insertion and empty-only bolt impulses.
    assert(EventPulse(.40f,.40f,.49f,.72f)==0);
    assert(EventPulse(.49f,.40f,.49f,.72f)==1);
    assert(EventPulse(.72f,.40f,.49f,.72f)==0);
    for(bool empty:{false,true}) {
        const float duration=empty ? 67.0f/30 : 58.0f/30;
        Motion removal=ReloadMotion(empty,(empty ? .49f : .52f)/duration);
        Motion seating=ReloadMotion(empty,(empty ? .99f : 1.06f)/duration);
        assert(removal.a[0]>.5f && removal.a[2]<-.4f);
        assert(seating.a[0]<-.5f && seating.a[2]>.3f);
        // Evaluate through the real filter: separate peaks must survive at
        // both 60 and 30 Hz, including a neutral interval between mag events.
        for(int step:{16,33}) {
            State reloadState;float removalPeak=0,insertionPeak=0,boltPeak=0;
            for(int ms=0;ms<int(duration*1000);ms+=step) {
                const float seconds=float(ms)*.001f;
                Motion motion=reloadState.Evaluate(ms,ScaleMotion(ReloadMotion(empty,seconds/duration),2.5f));
                if(seconds>.4f && seconds<.75f && motion.a[0]>removalPeak) {removalPeak=motion.a[0];}
                if(seconds>.9f && seconds<1.25f && -motion.a[0]>insertionPeak) {insertionPeak=-motion.a[0];}
                if(seconds>1.53f && seconds<1.84f && -motion.a[0]>boltPeak) {boltPeak=-motion.a[0];}
            }
            assert(removalPeak>1.25f && insertionPeak>1.25f);
            if(empty) {assert(boltPeak>.8f);} else {assert(boltPeak<.1f);}
            Motion reloadNeutral;Motion settled=reloadState.Evaluate(int(duration*1000)+1000,reloadNeutral);
            for(int i=0;i<3;++i) {assert(settled.a[i]==0 && settled.p[i]==0);}
        }
    }
    for(int step:{16,33}) {
        State throwState;float windupPeak=0,releasePeak=0,recoveryPeak=0;
        for(int ms=0;ms<1500;ms+=step) {
            const float seconds=float(ms)*.001f;
            Motion throwing=throwState.Evaluate(ms,ProfileMotion(Throw,seconds/(43.0f/30)));
            if(seconds<.22f && throwing.a[0]>windupPeak) {windupPeak=throwing.a[0];}
            if(seconds>.22f && seconds<.43f && -throwing.a[0]>releasePeak) {releasePeak=-throwing.a[0];}
            if(seconds>.48f && seconds<.9f && throwing.a[0]>recoveryPeak) {recoveryPeak=throwing.a[0];}
        }
        assert(windupPeak>.2f && releasePeak>.85f && recoveryPeak>.2f);
        Motion throwNeutral;Motion throwSettled=throwState.Evaluate(2200,throwNeutral);
        for(int i=0;i<3;++i) {assert(throwSettled.a[i]==0 && throwSettled.p[i]==0);}
    }
    assert(CompassTurns(0)==0 && CompassTurns(360)==0);
    assert(CompassTurns(90)==.25f && CompassTurns(-90)==.75f);
    assert(CompassTurns(720)==0);
    State walkA,walkB;Motion gaitA,gaitB;
    for(int t=0;t<=1000;t+=10) {gaitA=walkA.Walk(t,140,true);}
    for(int t=0;t<=1000;t+=20) {gaitB=walkB.Walk(t,140,true);}
    for(int i=0;i<3;++i) {assert(std::fabs(gaitA.a[i]-gaitB.a[i])<.0001f);}
    Motion repeated=walkA.Walk(1000,140,true);
    for(int i=0;i<3;++i) {assert(repeated.a[i]==gaitA.a[i]);}
    Motion stopped=walkA.Walk(1010,0,false);
    for(int i=0;i<3;++i) {assert(stopped.a[i]==0 && stopped.p[i]==0);}
    // The heavy shoulder kick is materially stronger, bounded, and clears
    // after a full pump interval. Same default output for AR/Magnum callers.
    for(int step:{8,16,33}) {
        State light,heavy;float lp=0,hp=0;
        light.Evaluate(0,neutral);heavy.Evaluate(0,neutral);
        light.Shot(0);heavy.Shot(0);
        for(int t=step;t<1100;t+=step) {
            Motion l=light.Evaluate(t,neutral,3.85f);
            Motion h=heavy.Evaluate(t,neutral,3.85f,true);
            lp=std::fmax(lp,-l.a[0]);hp=std::fmax(hp,-h.a[0]);
            for(int i=0;i<3;++i) {assert(std::isfinite(h.a[i]) && std::fabs(h.a[i])<=6);}
            if(t>250) {for(int i=0;i<3;++i) {assert(h.a[i]==0 && h.p[i]==0);}}
        }
        assert(hp>lp*1.55f && hp<4.1f);
    }
    // One shared gait: equal inputs yield equal motion for all three weapons.
    State gait[3];
    for(int t=0;t<3000;t+=16) {
        Motion ref=gait[0].Walk(t,140,true);
        for(int weapon=1;weapon<3;++weapon) {
            Motion v=gait[weapon].Walk(t,140,true);
            for(int axis=0;axis<3;++axis) {assert(v.a[axis]==ref.a[axis] && v.p[axis]==ref.p[axis]);}
        }
    }
    std::puts("PASS camera recovery, duplicate-query safety, rate independence, shot settling and bounds");
}
