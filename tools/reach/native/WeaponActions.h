// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_WEAPON_ACTIONS_H
#define REACH_WEAPON_ACTIONS_H
namespace ReachActions {
// Immediate first shot; only the following interval ramps. After300ms retain
// the accepted full interval exactly, including its fixed-tick-safe .066 value.
inline float M37FireInterval(int elapsedMs, float fullInterval, int rampMs) {
    if(rampMs<=0 || elapsedMs>=rampMs) {return fullInterval;}
    const float phase=elapsedMs<=0 ? 0.0f : float(elapsedMs)/float(rampMs);
    const float remaining=1.0f-phase;
    return fullInterval*(1.0f+.5f*remaining*remaining);
}
// One accepted attack edge per physical trigger hold. Caller resets on release.
inline bool Press(bool& consumed, bool down) {
    if(!down) {consumed=false;return false;}
    if(consumed) {return false;}
    consumed=true;return true;
}
}
#endif
