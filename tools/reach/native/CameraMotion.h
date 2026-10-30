#ifndef REACH_CAMERA_MOTION_H
#define REACH_CAMERA_MOTION_H
#include <cmath>

// Presentation state only: never serialized and never accumulates mouse angles.
namespace ReachCamera
{
struct Motion
{
    float p[3] = {0,0,0};
    float a[3] = {0,0,0}; // pitch, yaw, roll in degrees
};
inline Motion ScaleMotion( Motion motion, float gain )
{
    for( int i=0;i<3;++i ) {motion.p[i]*=gain;motion.a[i]*=gain;}
    return motion;
}
inline float Limit( float x, float lo, float hi ) { return x < lo ? lo : (x > hi ? hi : x); }
inline float Smooth( float x ) { x=Limit(x,0,1); return x*x*(3-2*x); }
inline float Bell( float t, float peak )
{
    if( t <= 0 || t >= 1 ) { return 0; }
    return t < peak ? Smooth(t/peak) : 1-Smooth((t-peak)/(1-peak));
}
enum Profile { None, Reload, ReloadEmpty, Raise, Lower, SprintEnter, SprintLoop, SprintExit, Throw };
inline float EventPulse( float seconds, float start, float peak, float end )
{
    if( seconds<=start || seconds>=end ) {return 0;}
    return seconds<peak ? Smooth((seconds-start)/(peak-start)) :
        1-Smooth((seconds-peak)/(end-peak));
}
inline Motion ReloadMotion( bool empty, float phase )
{
    Motion m;
    if( phase<=0 || phase>=1 ) {return m;}
    // Installed 30 Hz source clips: 59/68 frames, 58/67 frame intervals.
    // Magazine local tracks leave the receiver at frames 14/13 and reseat at
    // 31/29. Tactical reload adds the final seating tap near frame 40;
    // only empty reload moves b_ophandle forward at frames 48-50.
    const float seconds=phase*(empty ? 67.0f/30 : 58.0f/30);
    const float hold=Bell(phase,.36f);
    const float out=EventPulse(seconds,empty ? .36f : .40f,empty ? .46f : .49f,.72f);
    const float in=EventPulse(seconds,empty ? .87f : .93f,empty ? .96f : 1.03f,1.23f);
    const float seat=empty ? 0 : EventPulse(seconds,1.25f,1.32f,1.47f);
    const float bolt=empty ? EventPulse(seconds,1.52f,1.61f,1.81f) : 0;
    const float boltSettle=empty ? EventPulse(seconds,1.69f,1.80f,1.98f) : 0;
    // Low carrying motion between events; removal pulls down/left, seating
    // kicks up/right, bolt release gives a separate compact kick and rebound.
    m.p[0]=-.035f*hold-.070f*out+.075f*in+.020f*seat-.060f*bolt;
    m.p[1]= .025f*hold+.040f*out-.035f*in;
    m.p[2]=-.020f*hold-.040f*out+.045f*in+.015f*seat;
    m.a[0]= .140f*hold+.550f*out-.780f*in-.220f*seat-.520f*bolt+.160f*boltSettle;
    m.a[1]= .045f*hold+.130f*out-.100f*in+.070f*bolt;
    m.a[2]=-.160f*hold-.420f*out+.560f*in+.140f*seat+.300f*bolt-.100f*boltSettle;
    return m;
}
inline Motion M37ReloadMotion( bool empty, float seconds )
{
    Motion m;
    const float duration=empty ? 124.0f/30 : 119.0f/30;
    if( seconds<=0 || seconds>=duration ) {return m;}
    // M37 v2 source nodes at30Hz: tactical mag pull frames27-36, seat67-70,
    // final hand seating87-90. Empty: bolt12-27 BEFORE mag pull42-51,
    // insertion74-81, final seat90-93. Do not reuse the much shorter AR beat.
    const float hold=Bell(seconds/duration,.40f);
    const float out=EventPulse(seconds,empty ? 1.30f : .80f,empty ? 1.58f : 1.10f,empty ? 1.88f : 1.43f);
    const float in=EventPulse(seconds,empty ? 2.42f : 2.14f,empty ? 2.69f : 2.30f,empty ? 2.90f : 2.57f);
    const float seat=EventPulse(seconds,empty ? 2.94f : 2.82f,empty ? 3.10f : 3.00f,empty ? 3.31f : 3.23f);
    const float bolt=empty ? EventPulse(seconds,.35f,.64f,.80f) : 0;
    const float release=empty ? EventPulse(seconds,.72f,.84f,1.04f) : 0;
    m.a[0]=.12f*hold+.65f*out-.82f*in-.28f*seat-.58f*bolt+.22f*release;
    m.a[1]=.04f*hold+.15f*out-.11f*in+.07f*bolt;
    m.a[2]=-.14f*hold-.48f*out+.55f*in+.20f*seat+.32f*bolt-.13f*release;
    m.p[0]=-.04f*hold-.09f*out+.09f*in+.025f*seat-.065f*bolt;
    m.p[1]=.025f*hold+.045f*out-.035f*in;
    m.p[2]=-.025f*hold-.04f*out+.05f*in+.02f*seat;
    return m;
}
inline Motion ProfileMotion( Profile profile, float t )
{
    Motion m;
    if( profile==SprintLoop )
    {
        const float phase=6.28318530718f*t;
        m.a[0]=.18f*std::sin(phase*2);
        m.a[2]=.32f*std::sin(phase);
        return m; // vertical stride comes from the original camera_control track
    }
    if( t <= 0 || t >= 1 ) { return m; }
    if( profile==Throw )
    {
        // 44 frames at30Hz. Existing projectile release is267ms; let the
        // unchanged35ms camera response carry the release into follow-through.
        const float seconds=t*(43.0f/30);
        const float windup=EventPulse(seconds,.02f,.14f,.25f);
        const float release=EventPulse(seconds,.18f,.255f,.48f);
        const float recover=EventPulse(seconds,.38f,.54f,.88f);
        m.a[0]= .38f*windup-1.20f*release+.30f*recover;
        m.a[1]=-.18f*windup+.22f*release-.05f*recover;
        m.a[2]=-.32f*windup+.72f*release-.18f*recover;
        return m; // original camera_control translation is retained by caller
    }
    if( profile==Reload || profile==ReloadEmpty )
    {
        return ReloadMotion(profile==ReloadEmpty,t);
    }
    else if( profile==Raise )
    {
        const float lift=Bell(t,.36f), settle=Bell(Limit((t-.52f)/.48f,0,1),.35f);
        m.a[0]=.42f*lift-.13f*settle; m.a[2]=-.30f*lift+.10f*settle;
        m.p[2]=-.045f*lift;
    }
    else if( profile==Lower )
    {
        m.a[0]=.24f*Bell(t,.45f); m.a[2]=.17f*Bell(t,.45f);
    }
    else if( profile==SprintEnter )
    {
        m.a[0]=.26f*Bell(t,.55f); m.a[2]=-.20f*Bell(t,.55f);
    }
    else if( profile==SprintExit )
    {
        const float plant=Bell(t,.22f), settle=Bell(Limit((t-.30f)/.70f,0,1),.35f);
        m.a[0]=.38f*plant-.16f*settle; m.a[2]=.23f*plant-.10f*settle;
    }
    return m;
}
inline float ShotPulse( int age )
{
    if( age <= 0 || age >= 165 ) { return 0; }
    return age < 18 ? Smooth(float(age)/18.0f) : 1-Smooth(float(age-18)/147.0f);
}
inline float CompassTurns( float yaw )
{
    if( !std::isfinite(yaw) ) {return 0;}
    return (yaw-std::floor(yaw/360.0f)*360.0f)/360.0f;
}
inline Motion WalkingMotion( float phase, float strength )
{
    Motion m;const float p=6.28318530718f*phase;
    strength=Limit(strength,0,1.25f);
    m.a[0]=.225f*std::sin(p*2)*strength;
    m.a[1]=.06875f*std::sin(p)*strength;
    m.a[2]=.30f*std::sin(p)*strength;
    m.p[2]=.09375f*std::sin(p*2)*strength;
    return m;
}
struct State
{
    Motion filtered;
    int walkTime=-1;
    float walkPhase=0;
    int lastTime=-1;
    int shotTime[4]={-100000,-100000,-100000,-100000};
    int shotSide[4]={1,-1,1,-1};
    int nextShot=0, sequence=0, lastShot=-1, debugTime=-1;
    void Reset()
    {
        walkTime=-1;walkPhase=0;
        filtered=Motion();lastTime=-1;nextShot=sequence=0;lastShot=debugTime=-1;
        for( int i=0;i<4;++i ) { shotTime[i]=-100000;shotSide[i]=1; }
    }
    Motion Walk( int now, float speed, bool active )
    {
        if( walkTime<0 || now<walkTime || now-walkTime>250 ) {walkTime=now;}
        const float elapsed=float(now-walkTime)*.001f;walkTime=now;
        if( !std::isfinite(speed) || speed<0 ) {speed=0;}
        if( !active ) {return Motion();}
        walkPhase+=elapsed*Limit(speed,0,320)/140.0f;
        walkPhase-=std::floor(walkPhase);
        return WalkingMotion(walkPhase,Limit(speed/140.0f,0,1.25f));
    }
    void Shot( int now )
    {
        if( now==lastShot ) { return; }
        lastShot=now;shotTime[nextShot]=now;shotSide[nextShot]=(sequence++&1) ? -1 : 1;
        nextShot=(nextShot+1)%4;
    }
    Motion Evaluate( int now, const Motion& target, float shotScale=1, bool heavyShot=false )
    {
        if( lastTime>=0 && now<lastTime ) { Reset(); }
        if( lastTime<0 || now<lastTime || now-lastTime>250 )
        {
            filtered=Motion();lastTime=now;
        }
        const float dt=float(now-lastTime)*.001f;
        // Exact exponential response: duplicate view queries do not integrate
        // twice; frame rate changes do not change the settling time.
        const float blend=1-std::exp(-dt/.035f);
        for( int i=0;i<3;++i )
        {
            filtered.p[i]+=(target.p[i]-filtered.p[i])*blend;
            filtered.a[i]+=(target.a[i]-filtered.a[i])*blend;
            if( std::fabs(filtered.p[i])<.00001f && target.p[i]==0 ) { filtered.p[i]=0; }
            if( std::fabs(filtered.a[i])<.00001f && target.a[i]==0 ) { filtered.a[i]=0; }
        }
        lastTime=now;
        Motion result=filtered;
        for( int i=0;i<4;++i )
        {
            const int age=now-shotTime[i];
            const float impulse=heavyShot ? (age<=0 || age>=205 ? 0 :
                (age<18 ? Smooth(float(age)/18) : 1-Smooth(float(age-18)/187))) : ShotPulse(age);
            const float pulse=impulse*Limit(shotScale,0,4);
            // M45: a heavier shoulder impulse, then a small damped settle.
            // Default path keeps the accepted AR and Magnum response exact.
            const float settle=heavyShot ? EventPulse(float(now-shotTime[i])*.001f,
                .12f,.19f,.28f)*Limit(shotScale,0,4) : 0;
            result.a[0]-=(heavyShot ? 1.42f : .66f)*pulse-.18f*settle;
            result.a[1]+=.075f*float(shotSide[i])*pulse;
            result.a[2]+=(heavyShot ? .24f : .12f)*float(shotSide[i])*pulse;
            result.p[0]-=(heavyShot ? .15f : .035f)*pulse;
            result.p[2]+=(heavyShot ? .055f : .025f)*pulse;
            if(heavyShot && age>0 && age<150) {
                // Compact damped shoulder vibration; presentation only.
                const float seconds=float(age)*.001f;
                const float shake=std::sin(seconds*88)*std::exp(-seconds*24)*Smooth(float(age)/8);
                result.a[1]+=.28f*shake*float(shotSide[i]);
                result.a[2]+=.38f*shake*float(shotSide[i]);
            }
        }
        float length=0;
        for( int i=0;i<3;++i ) { length+=result.p[i]*result.p[i];result.a[i]=Limit(result.a[i],-6.0f,6.0f); }
        if( length>4 ) { const float scale=2/std::sqrt(length);for(float& v:result.p) {v*=scale;} }
        return result;
    }
};
}
#endif
