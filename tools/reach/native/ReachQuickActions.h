#ifndef REACH_QUICK_ACTIONS_H
#define REACH_QUICK_ACTIONS_H
namespace ReachQuickActions
{
// Slots 23/24 exist in this exact host's usercmd generator and are unhandled
// by its player impulse switch. Read the byte sequence to avoid held-key repeats.
inline int Read( int sequence, int previous, int impulse )
{
	if( sequence == previous ) { return 0; }
	return impulse == 23 ? 1 : ( impulse == 24 ? 2 : 0 );
}
inline int BounceFuseDelay( int now, int launch, int arming, int timer )
{
	const int armingRemaining = launch + arming - now;
	return armingRemaining > timer ? armingRemaining : timer;
}
}
#endif
