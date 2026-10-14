Reach rifle angle update r10 - keeps your r9 position and r8 projection

1. Close the game. Extract this ZIP beside ReachRBDoom3BFG.exe.
   Replace reach/zzzzzz_reach_position.pk4 when prompted.
2. Start the same Play-Reach-projection.cmd. Keep the gun settings you just
   tested: g_gunX -4, g_gunY 4, g_gunZ 1. This update does not set them.
3. Test in a fresh map first: the weapon script has changed. Earlier saves
   may not be compatible with the changed script program.
4. Compare the idle rifle, then check fire/flash, reload and sprint.

The default is a small -3-degree roll, with pitch and yaw left at zero.
It rotates the complete rig around the idle counter center, keeping that
point fixed while slightly flattening the receiver angle. This is a trial,
not a verified 1:1 Reach pose. All clips and the original root orientation
are retained. The correction runs on weapon initialization and Raise.

Optional rifle-only angle controls in the game console:
    set reach_arPitch 0
    set reach_arYaw 0
    set reach_arRoll -3
Switch to another weapon and back after changing a value. No manual exec
is needed. Angles are degrees. They do not move the world camera or other
weapons. Set all three to zero to compare with your unrotated r9 pose.
Use seta instead of set if you want to retain custom angles after quitting.
There are no new per-frame script checks or loops.

This replaces the r9 overlay but keeps its offset (4, -4.2, -2.8). It does
not set g_gunX/Y/Z/Scale, world FOV, weapon FOV, display or threading options.
The accepted executable, launchers, counter materials and gameplay states
are retained. No executable, DLL, shader or extracted game asset is included.

To return to r9, close the game and replace the PK4 with the one from your
r9 ZIP. Keep reach/zzzzz_reach_projection.pk4 installed in either case.
Runtime framing and script loading still need your in-game check.
