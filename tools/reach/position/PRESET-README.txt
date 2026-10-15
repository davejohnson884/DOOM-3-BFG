Reach AR position preset r12 - rifle-only offsets applied automatically

1. Close the game. Extract this ZIP beside ReachRBDoom3BFG.exe.
2. Overwrite both Play-Reach-projection CMD files and the position PK4.
   Copy the included reach/reach_pose.cfg as well.
3. Launch Play-Reach-projection.cmd. No manual exec or g_gun edits are needed.
   Test a fresh map first because the rifle presentation script has changed.

Your chosen -4, 4, 1 anchor now belongs only to the Reach assault rifle:
    reach_arGunX -4
    reach_arGunY 4
    reach_arGunZ 1
The preset restores g_gunX/Y/Z to Doom's stock defaults, undoing the earlier
manual global edits. Other weapons retain their normal placement. The rifle
script adds its own scale-corrected root translation and the existing
-3-degree roll. It does not set any global cvar or add frame polling.

The game console prints "Reach AR r12 pose preset loaded" and the six
rifle-specific position/angle settings. Both normal and diagnostic CMDs
load the preset after saved startup settings. A missing preset or overlay
stops the launcher with an explanation.

The accepted projection, executable and r9 model offset are retained. The
shift is based on your original g_gun anchor, not a second -4/4/1 translation
added on top. The script accounts for the current g_gunScale without setting
it. Gun bob and animation still move the rig naturally.

For later rifle-only tuning, edit the included short CFG, or use
set reach_arGunX / reach_arGunY / reach_arGunZ and the existing
reach_arPitch / reach_arYaw / reach_arRoll console controls. Reselect the
rifle after console edits. The CFG is applied again on each preset launch.

Keep the r8 projection files, including ReachRBDoom3BFG.exe and
reach/zzzzz_reach_projection.pk4, installed. No executable, DLL, shader,
animation or extracted game asset is included. World FOV, display and
threading options are not changed. Older script saves may be incompatible.

Package, translation math and Windows CMD/config fixtures were checked.
The game was not run in the cloud; owner framing and action checks remain.
