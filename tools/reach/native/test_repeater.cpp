// SPDX-License-Identifier: GPL-3.0-or-later
#include "RepeaterHeat.h"
#include <cstdio>
#include <cstdlib>
static void Check(bool ok,const char* message) {if(!ok) {std::fprintf(stderr,"%s\n",message);std::exit(1);}}
int main() {
 Check(ReachRepeater::Rate(0)==15 && ReachRepeater::Rate(1)==3,"cadence endpoints");
 float last=15;for(int i=0;i<=1000;++i) {float r=ReachRepeater::Rate(i/1000.0f);Check(r<=last && r>=3,"heat cadence monotonic");last=r;}
 float h=0;int battery=100;for(int i=0;i<40;++i) {h=ReachRepeater::Shot(h);--battery;}
 Check(h==1 && battery==60,"battery and heat independent at saturation");
 float fine=1,coarse=1;for(int i=0;i<600;++i) {fine=ReachRepeater::Cool(fine,1/120.0f,false,false);}for(int i=0;i<150;++i) {coarse=ReachRepeater::Cool(coarse,1/30.0f,false,false);}
 Check(std::fabs(fine-coarse)<.001f,"frame rate independent passive cooling");
 Check(ReachRepeater::Cool(1,2.5f,true,false)==0 && battery==60,"vent cannot refill battery");
 Check(ReachRepeater::Cool(1,30,false,false)==0,"holstered cooling");
 Check(ReachRepeater::Cool(.7f,1,false,true)==.7f,"no passive cooling while firing");
 std::puts("Repeater heat/battery/cadence checks passed");
}
