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
inline float Limit( float x, float lo, float hi ) { return x < lo ? lo : (x > hi ? hi : x); }
inline float Smooth( float x ) { x=Limit(x,0,1); return x*x*(3-2*x); }
inline float Bell( float t, float peak )
{
    if( t <= 0 || t >= 1 ) { return 0; }
    return t < peak ? Smooth(t/peak) : 1-Smooth((t-peak)/(1-peak));
}
enum Profile { None, Reload, ReloadEmpty, Raise, Lower, SprintEnter, SprintLoop, SprintExit };
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
    if( profile==Reload || profile==ReloadEmpty )
    {
        const float settle=Bell(t,.40f);
        const float insert=Bell(Limit((t-.48f)/.28f,0,1),.42f);
        m.p[0]=-.12f*settle+.035f*insert;
        m.p[1]=.09f*settle-.04f*insert;
        m.p[2]=-.06f*settle;
        m.a[0]=.72f*settle-.38f*insert;
        m.a[1]=.16f*settle-.12f*insert;
        m.a[2]=-.68f*settle+.34f*insert;
        if( profile==ReloadEmpty )
        {
            const float bolt=Bell(Limit((t-.73f)/.23f,0,1),.32f);
            m.a[0]-=.28f*bolt; m.a[2]+=.18f*bolt;
        }
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
struct State
{
    Motion filtered;
    int lastTime=-1;
    int shotTime[4]={-100000,-100000,-100000,-100000};
    int shotSide[4]={1,-1,1,-1};
    int nextShot=0, sequence=0, lastShot=-1, debugTime=-1;
    void Reset()
    {
        filtered=Motion();lastTime=-1;nextShot=sequence=0;lastShot=debugTime=-1;
        for( int i=0;i<4;++i ) { shotTime[i]=-100000;shotSide[i]=1; }
    }
    void Shot( int now )
    {
        if( now==lastShot ) { return; }
        lastShot=now;shotTime[nextShot]=now;shotSide[nextShot]=(sequence++&1) ? -1 : 1;
        nextShot=(nextShot+1)%4;
    }
    Motion Evaluate( int now, const Motion& target )
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
            const float pulse=ShotPulse(now-shotTime[i]);
            result.a[0]-=.66f*pulse;
            result.a[1]+=.075f*float(shotSide[i])*pulse;
            result.a[2]+=.12f*float(shotSide[i])*pulse;
            result.p[0]-=.035f*pulse;
            result.p[2]+=.025f*pulse;
        }
        float length=0;
        for( int i=0;i<3;++i ) { length+=result.p[i]*result.p[i];result.a[i]=Limit(result.a[i],-3.5f,3.5f); }
        if( length>4 ) { const float scale=2/std::sqrt(length);for(float& v:result.p) {v*=scale;} }
        return result;
    }
};
}
#endif

