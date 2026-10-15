Reach position preset r11 - automatically applies your gun settings

1. Close the game. Extract this ZIP beside ReachRBDoom3BFG.exe.
2. Overwrite both Play-Reach-projection CMD files and the position PK4.
   Copy the included reach/reach_pose.cfg as well.
3. Launch Play-Reach-projection.cmd. No manual console exec or gun settings
   are needed. Select another weapon and then the rifle to reapply its pose.

The new launcher loads this short preset after saved startup settings:
    g_gunX -4
    g_gunY 4
    g_gunZ 1
    reach_arPitch 0
    reach_arYaw 0
    reach_arRoll -3
The console prints "Reach r11 pose preset loaded" followed by those actual
cvar values. If the preset file or overlay is missing, the launcher stops
and identifies the missing installation file.

The script, model offset and -3-degree roll are identical to r10. This update
fixes automatic loading of your position and the angle preset. If you already
had all six values applied in r10, the appearance should remain the same.
No new executable, DLL, shader, animation or extracted game asset is included.
Gun scale, world FOV, display and threading settings are not set by the preset.
It loads the existing r8 projection config before applying the six values.

The g_gun values are the engine's global weapon offsets, as when you set them
manually. Angle controls remain rifle-only. You can edit the included small
CFG to retain later tuning; console changes last until the next preset launch.

Keep the r8 projection files, including ReachRBDoom3BFG.exe and
reach/zzzzz_reach_projection.pk4, installed. The diagnostic CMD uses the
existing ReachDebugLog.exe if needed. Normal play launches the game directly.

R11 adds no script changes relative to r10. Saves made with older weapon
scripts may still be incompatible. Packaging and Windows launch/config
fixtures were checked; the game was not run in the cloud.
