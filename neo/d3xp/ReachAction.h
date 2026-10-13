#ifndef __GAME_REACH_ACTION_H__
#define __GAME_REACH_ACTION_H__

enum reachActionKind_t { REACH_ACTION_NONE, REACH_ACTION_MELEE, REACH_ACTION_GRENADE };

// A pending effect is consumed at most once. Inventory/damage belongs to the
// caller, at effect time; cancelling a windup therefore spends nothing.
class reachAction_t {
public:
	reachAction_t() { Reset(); }
	void Reset() { kind = REACH_ACTION_NONE; effectDone = true; effectTime = finishTime = 0; }
	bool BlocksWeapon( int now ) const { return !effectDone || now < finishTime; }
	reachActionKind_t CurrentKind( int now ) const { return BlocksWeapon( now ) ? kind : REACH_ACTION_NONE; }
	bool Begin( reachActionKind_t requested, int now, int windupMS, int recoveryMS ) {
		if ( requested == REACH_ACTION_NONE || BlocksWeapon( now ) ) { return false; }
		kind = requested;
		effectDone = false;
		effectTime = now + ( windupMS > 0 ? windupMS : 0 );
		finishTime = effectTime + ( recoveryMS > 0 ? recoveryMS : 0 );
		return true;
	}
	reachActionKind_t ConsumeEffect( int now ) {
		if ( effectDone || now < effectTime ) { return REACH_ACTION_NONE; }
		effectDone = true;
		return kind;
	}
	void CancelPending() { effectDone = true; kind = REACH_ACTION_NONE; }
private:
	reachActionKind_t kind;
	bool effectDone;
	int effectTime;
	int finishTime;
};

#endif
