// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef REACH_FUEL_ROD_POLICY_H
#define REACH_FUEL_ROD_POLICY_H
#include <cmath>
namespace ReachFuelRod {
// Source WU -> host conversion is120; acceleration bounds4.5..5 WU.
inline float Speed(float distance) {
    float t=(distance-540.0f)/60.0f;t=t<0 ? 0 : (t>1 ? 1 : t);
    return 1800.0f-1020.0f*t;
}
inline bool Bounce(bool actor,float speed,float incidence) {
    return !actor && std::isfinite(speed) && std::isfinite(incidence) &&
        speed>=1680.0f && speed<=2400.0f && incidence>0 && incidence<=.70710678f;
}
}
#endif
