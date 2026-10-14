Reach rifle position update r9 - for the r8 projection candidate

1. Close the game. Extract this ZIP into the folder containing
   ReachRBDoom3BFG.exe and your existing reach folder.
2. Keep the r8 projection files installed. Start the same
   Play-Reach-projection.cmd you just tested. No console exec is needed.
3. After selecting the rifle, stand still and let it finish raising.
   Compare the counter, receiver and hands with the Reach reference.
   Also check reload, sprint and the muzzle flash.

This adds reach/zzzzzz_reach_position.pk4. It changes only the model
declaration's position: forward 7 units, right 4.2, down 1.6 relative to r8.
The same translation applies to the rifle, hands, animations and attached
muzzle marker. The accepted projection, executable and launchers are retained.

This is a reference-guided first fit, not a verified 1:1 Reach preset. Saved
g_gunX/Y/Z/Scale values, screenshot cropping and animation movement can affect
the comparison. No world FOV, display or threading setting is set by this ZIP.

To undo this position change, close the game and remove only
reach/zzzzzz_reach_position.pk4. Keep the r8 projection overlay installed.

The optional r8 diagnostic script still prints its original offset in the
"projection tagged" line; this higher-priority declaration supplies the r9
offset (4, -4.2, -2.8). The script itself has not been changed.

No executable, DLL, shader, game asset or animation is included in this update.
Package checks passed; this position has not been tested in a running game here.
