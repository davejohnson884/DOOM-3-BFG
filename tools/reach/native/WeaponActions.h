// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_WEAPON_ACTIONS_H
#define REACH_WEAPON_ACTIONS_H
namespace ReachActions {
// One accepted attack edge per physical trigger hold. Caller resets on release.
inline bool Press(bool& consumed, bool down) {
    if(!down) {consumed=false;return false;}
    if(consumed) {return false;}
    consumed=true;return true;
}
}
#endif
