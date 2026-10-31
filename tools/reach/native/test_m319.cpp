#include "M319Policy.h"
#include <cassert>
int main() {
 using namespace ReachM319;
 assert(Step(Holding,false,100,false)==Normal);
 assert(Step(Holding,true,299,false)==Holding);
 assert(Step(Holding,true,300,false)==Armed);
 assert(Step(Holding,true,40,true)==Armed);
 assert(Step(Armed,false,320,false)==Remote);
 assert(Step(Normal,true,800,true)==Normal);
 assert(Step(Remote,true,800,true)==Remote);
 assert(RemainingFuse(350,100)==250);
 assert(RemainingFuse(900,100)==0);
 assert(DirectImpact(false,true,1000,.2f));
 assert(!DirectImpact(true,true,1500,1));
 assert(!DirectImpact(false,true,599,1));
 assert(!DirectImpact(false,false,1500,.8f));
 assert(DirectImpact(false,false,1500,.98f));
}
