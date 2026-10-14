Reach rifle projection candidate r8

This uses the source of your RBDOOM-3-BFG 1.6.0.22 / May 10 2025 release,
commit ba39ba67df049dcf16c7b31f6613f72959be2c21. It adds a separate executable
named ReachRBDoom3BFG.exe. It is a test candidate, not a verified 1:1 Reach preset.

1. Close the game. Extract this ZIP into the folder containing your existing
   RBDoom3BFG.exe, its published support files, and the installed reach folder.
2. Double-click Play-Reach-projection.cmd. Use a fresh single-player map for
   this first test and select the machinegun / Reach rifle.
3. Check idle framing, firing and the counter/flash, then reload and sprint.
   Test your normal 3440x1440 display. A 16:9 comparison is useful if available.

This is a normal CMD launch, without PowerShell. The published RBDoom3BFG.exe,
its DLLs/shaders, world FOV and display/thread settings are retained. The new
executable defaults to its original projection until the candidate config
enables the Reach-only control. Ordinary Doom weapons use the original path.

The initial weapon FOV comes from a real public Reach MA37 SWEP: 54 degrees
horizontal at 4:3 (about 68.38 at 16:9). It is not a recovered Reach retail
constant. The r7 added root rotation and excessive pullback are removed. The
offset cancels BFG's default +3 forward gun offset and uses Reach's decoded
centered -1.2 vertical offset. Other g_gun settings are not overwritten.
The original meshes, weights and animation clips are not deformed or replaced.

The rifle and first-person flash use the same weapon projection. This can be
tuned in the console with r_reachWeaponFov; 0 disables the new projection.
The on-model ammo counter remains on the rifle. Existing fire/reload/sprint,
impact normalization and V control logic are retained. This change does not
claim to fix the pending V input issue or implement G quick grenades.

No game was run in the cloud. Build/package/camera checks do not establish
graphics correctness or stability on your PC. Use new test saves for this
candidate; compatibility with earlier mod-script saves is not established.

If there is a runtime problem, Play-Reach-projection-diagnostic.cmd uses the
existing debug-output reader and selects Reach-weapon-debug.log on exit.
Normal play does not use the diagnostic helper.

To return to the previous mod, close the game, remove only
reach/zzzzz_reach_projection.pk4, and use your existing Play-Reach.cmd.
Your published executable and original mod archive remain installed.

Sources: upstream release source plus the included patch/header. Rebuild tools
are in source/native and the public project repository:
https://github.com/davejohnson884/DOOM-3-BFG/tree/reach-combat/tools/reach/native
Upstream: https://github.com/RobertBeckebans/RBDOOM-3-BFG/tree/ba39ba67df049dcf16c7b31f6613f72959be2c21
Licenses are included. This ZIP contains no extracted Halo or Doom game assets.
