# First combat prototype playtest

This build adds optional sprint, quick melee and quick grenade controls. It uses BFG weapons, fists damage and grenade assets. Reach models, hands, animations, sound and exact balance are not imported yet. The gun lowers during quick actions; there is no Reach punch/throw animation.

Extract the entire `reach-bfg-win32` artifact into a new folder outside Steam. Close any running BFG/RBDoom/BFA game, then double-click `Start-Reach-playtest.cmd`. No administrator access is needed. The launcher checks the executable against the included build checksum, copies the stock BFG save/profile directory into a backup if it exists, and creates a new lab profile for this run. It does not replace Steam executables or alter the original profile. The checksum checks package consistency; GitHub's artifact is the build provenance.

Start an offline campaign or open the in-game console with `~` and enter these commands one at a time:

```
devmap game/alphalabs1
give all
```

Wait for the level to finish loading before entering `give all`. This is BFG's in-game console; no Windows terminal commands are needed. The introductory Mars City level disables weapons and is unsuitable for this test. `give all` supplies test weapons/ammo; the prototype does not grant grenades during normal play.

The launcher enables `g_reachLabAutoConfig`, so the player loads `reach_prototype.cfg` after spawning or loading a save. This reapplies V/G bindings after the profile's default controls and restores the test movement tuning. The console should print `[Reach] lab controls loaded: Shift sprint, V melee, G grenade`. To reapply manually, enter `exec reach_prototype.cfg`. If testing an older package with the hyphenated filename, use `exec "reach-prototype.cfg"` with the quotes.

- Equip the machinegun. Hold forward + Shift: it should sprint with the gun lowered. Release Shift and fire: firing should resume after recovery.
- Press V near a damageable target, then facing empty space: logs should report one hit or miss per accepted action. The weapon should stay in the same slot. Try rapid V/G inputs; actions should not overlap.
- Press G with the machinegun equipped: one BFG grenade should spawn after the windup. The console log should say `grenade resolved: thrown; ammo=...`, with the grenade count reduced once. Repeated presses during recovery should not consume more ammo.
- Face a nearby wall and throw: the grenade should remain on your side of the wall. If no safe spawn position exists, the action should report `blocked` and retain its ammo.
- Try switching weapons during the windup, opening the PDA, and saving/loading: a cancelled pending action must produce no extra hit/throw. Already spawned grenades and consumed inventory follow normal BFG save behavior. Transient action timers reset on load.

Close the game normally. Send `profile/reach_lab/qconsole.log` from the new `playtest-...` folder and describe which checks worked or failed; a short clip of V/G/Shift helps validate presentation. Keep backup/profile data private. If startup fails, send the error and the log if one was created. To return to your usual game, launch its original Steam/RBDoom/BFA executable normally.
