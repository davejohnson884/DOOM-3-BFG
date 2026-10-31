#include "SpartanModelAliases.h"
#include <cassert>
int main() {
    assert(ReachSpartan::Replacement(NULL)==NULL);
    assert(ReachSpartan::Replacement("models/md5/characters/npcs/playermoves/mpplayer.md5mesh")==NULL);
    assert(ReachSpartan::Replacement("models/md5/monsters/zsec/zsec.md5mesh")==NULL);
    assert(ReachSpartan::Replacement("models/md5/weapons/reach_m37/view.md5mesh")==NULL);
    for (const ReachSpartan::Alias& alias : ReachSpartan::aliases) {
        assert(std::strcmp(ReachSpartan::Replacement(alias.from),alias.to)==0);
        assert(ReachSpartan::Replacement(alias.to)==NULL);
    }
    assert(sizeof(ReachSpartan::aliases)/sizeof(ReachSpartan::aliases[0])==22);
}
