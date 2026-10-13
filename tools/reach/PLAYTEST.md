# First combat prototype playtest

This build adds optional sprint, quick melee and quick grenade controls. It uses BFG weapons, fists damage and grenade assets. Reach models, hands, animations, sound and exact balance are not imported yet. The gun lowers during quick actions; there is no Reach punch/throw animation.

Extract the entire `reach-bfg-win32` artifact into a new folder outside Steam. Close any running BFG/RBDoom/BFA game, then double-click `Start-Reach-playtest.cmd`. No administrator access is needed. The launcher checks the executable against the included build checksum, copies the stock BFG save/profile directory into a backup if it exists, and creates a new lab profile for this run. It does not replace Steam executables or alter the original profile. The checksum checks package consistency; GitHub's artifact is the build provenance.

The game now starts in borderless fullscreen at the primary desktop's resolution. Normal logging writes `qconsole.log` with timestamps and avoids flushing the disk after every message. If the game pauses or stops responding, note what you were doing and send that session's log. These settings address the small window and logging overhead; they do not establish that every freeze is fixed. For developer troubleshooting, the launcher accepts `-Windowed` (1280 x 720) and `-FlushLog` (flush after each message).

The owner reports the single-threaded Reach diagnostic plays normally, while the compiled stock-combat test with normal threading freezes. The requested final target preserves stock threading/performance behavior, so `Start-Reach-playtest.cmd` uses the original threading defaults. `Start-Reach-diagnostic.cmd` remains an optional comparison, not the normal mod configuration. The source build has not met the stock stability target and should not be presented as the finished mod. Monster death rules, blood settings and gib eligibility are unchanged.

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

## Freeze/crash comparison

The owner reports Steam's original BFG runs smoothly, while this source build can freeze with a responsive menu. The latest log shows successful 3440 x 1440 startup and a long map load, but no fatal error explaining that freeze. These launchers collect evidence; they are not confirmed fixes.

1. Double-click `Start-Stock-baseline.cmd`. This uses our executable with Reach combat and its automatic config disabled, using the engine's normal threading. Enter `devmap game/alphalabs1`, wait for loading, then move around for a few minutes. Do not exec the Reach config during this comparison. Note whether it freezes.
2. Close that game. Double-click `Start-Reach-diagnostic.cmd`. This keeps Reach controls but runs game/draw and renderer jobs on the main thread. Load the same level, use `give all`, and repeat movement and Shift/V/G. Note whether it freezes.
3. Close each test through the menu if possible. If it becomes entirely unresponsive, close its process in Task Manager and leave the launcher open so it can finish collecting the report. Each test creates a `reach-diagnostics-...zip` beside the launcher. Send both ZIPs with the results.

The reports include only the console logs and their location index, launch settings/binary hash, CPU/GPU/driver names and system memory, process memory/responsiveness samples, exit status and matching Windows crash events when available. They exclude backup profiles, saves and game assets. The launcher gives the log an explicit path at `playtest-.../qconsole.log`, and also collects any fallback logs inside that session's profile. Frame log lines record whether game time advances, pause/menu/control state and the threading mode. Diagnostic death lines record enemy/damage definitions, health, normal gib eligibility, blood setting and burn delay without changing those behaviors. Windows crash events can arrive after the launcher exits, so absence of an event does not rule out a crash.

The first compiled stock-combat baseline also stuttered and froze. Its process report stayed responsive, used around 1 GB of private memory and exited normally; the report lacked a console log. Resident memory dropped sharply after loading, matching the engine's explicit Windows working-set eviction at the end of a map load. Removing that eviction was investigated, then reverted at the owner's request to preserve stock memory/performance policy. The persistent freeze with normal threading remains unresolved.
