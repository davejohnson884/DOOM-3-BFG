// Reach-only saved player mesh aliases. No game assets or save-format changes.
#ifndef REACH_SPARTAN_MODEL_ALIASES_H
#define REACH_SPARTAN_MODEL_ALIASES_H
#include <cstddef>
namespace ReachSpartan {
struct Alias { const char* from; const char* to; };
static const Alias aliases[] = {
    {"models/md5/characters/npcs/playermoves/spplayer.md5mesh", "models/reach/characters/noble_six/characters/npcs/playermoves/spplayer.md5mesh"},
    {"models/md5/characters/player/d3xp_spplayer.md5mesh", "models/reach/characters/noble_six/characters/player/d3xp_spplayer.md5mesh"},
    {"models/md5/characters/player/head/d3xp_head.md5mesh", "models/reach/characters/noble_six/characters/player/head/d3xp_head.md5mesh"},
    {"models/md5/characters/player/mocap/mgplayer.md5mesh", "models/reach/characters/noble_six/characters/player/mocap/mgplayer.md5mesh"},
    {"models/md5/characters/player/mocap/player.md5mesh", "models/reach/characters/noble_six/characters/player/mocap/player.md5mesh"},
    {"models/md5/characters/player/mocap/wepplayer.md5mesh", "models/reach/characters/noble_six/characters/player/mocap/wepplayer.md5mesh"},
    {"models/md5/cinematics/erebus2/player_grabber.md5mesh", "models/reach/characters/noble_six/cinematics/erebus2/player_grabber.md5mesh"},
    {"models/md5/cinematics/erebus2/player_orb.md5mesh", "models/reach/characters/noble_six/cinematics/erebus2/player_orb.md5mesh"},
    {"models/md5/cinematics/erebus2/player_vulgarintro.md5mesh", "models/reach/characters/noble_six/cinematics/erebus2/player_vulgarintro.md5mesh"},
    {"models/md5/cinematics/erebus5/e5_player.md5mesh", "models/reach/characters/noble_six/cinematics/erebus5/e5_player.md5mesh"},
    {"models/md5/cinematics/erebus6/player.md5mesh", "models/reach/characters/noble_six/cinematics/erebus6/player.md5mesh"},
    {"models/md5/cinematics/erebus6/player_outro.md5mesh", "models/reach/characters/noble_six/cinematics/erebus6/player_outro.md5mesh"},
    {"models/md5/cinematics/hell/maledict_intro/player_maledict_intro.md5mesh", "models/reach/characters/noble_six/cinematics/hell/maledict_intro/player_maledict_intro.md5mesh"},
    {"models/md5/cinematics/intro/player_heartartifact.md5mesh", "models/reach/characters/noble_six/cinematics/intro/player_heartartifact.md5mesh"},
    {"models/md5/cinematics/intro/player_helmet.md5mesh", "models/reach/characters/noble_six/cinematics/intro/player_helmet.md5mesh"},
    {"models/md5/cinematics/maledict_death/player_heartartifact_end.md5mesh", "models/reach/characters/noble_six/cinematics/maledict_death/player_heartartifact_end.md5mesh"},
    {"models/md5/cinematics/maledict_death/player_rocketlauncher_end.md5mesh", "models/reach/characters/noble_six/cinematics/maledict_death/player_rocketlauncher_end.md5mesh"},
    {"models/md5/cinematics/maledict_death/player_turnrun_end.md5mesh", "models/reach/characters/noble_six/cinematics/maledict_death/player_turnrun_end.md5mesh"},
    {"models/md5/cinematics/phobos2/player.md5mesh", "models/reach/characters/noble_six/cinematics/phobos2/player.md5mesh"},
    {"models/md5/cinematics/phobos2/playeroutro.md5mesh", "models/reach/characters/noble_six/cinematics/phobos2/playeroutro.md5mesh"},
    {"models/md5/cinematics/revenant/revintro_player2.md5mesh", "models/reach/characters/noble_six/cinematics/revenant/revintro_player2.md5mesh"},
    {"models/md5/heads/player/player.md5mesh", "models/reach/characters/noble_six/heads/player/player.md5mesh"},
};
inline bool Equal(const char* a, const char* b) {
    while (*a != 0 && *a == *b) { ++a; ++b; }
    return *a == *b;
}
inline const char* Replacement(const char* canonical) {
    if (canonical == NULL) { return NULL; }
    for (const Alias& entry : aliases) {
        if (Equal(canonical, entry.from)) { return entry.to; }
    }
    return NULL;
}
}
#endif

