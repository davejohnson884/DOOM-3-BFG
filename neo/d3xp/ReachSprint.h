#ifndef __GAME_REACH_SPRINT_H__
#define __GAME_REACH_SPRINT_H__

// Transient single-player action state. Loading a save cancels sprint/recovery;
// stamina remains in BFG's existing serialized player state.
class reachSprint_t {
public:
	reachSprint_t() { Reset(); }
	void Reset() { active = false; readyTime = 0; }
	bool IsActive() const { return active; }
	bool BlocksWeapon( int now ) const { return active || now < readyTime; }
	bool HasCharge( float charge, float capacity, float minimumFraction ) const {
		if ( capacity <= 0.0f ) { return true; }
		if ( charge <= 0.0f ) { return false; }
		return active || charge >= capacity * minimumFraction;
	}
	void Stop( int now, int recoveryMS ) {
		if ( active ) {
			active = false;
			readyTime = now + ( recoveryMS > 0 ? recoveryMS : 0 );
		}
	}
	void Update( bool requested, bool allowed, int now, int recoveryMS ) {
		if ( !requested || !allowed ) {
			Stop( now, recoveryMS );
		} else if ( now >= readyTime ) {
			active = true;
		}
	}
private:
	bool active;
	int readyTime;
};

#endif
