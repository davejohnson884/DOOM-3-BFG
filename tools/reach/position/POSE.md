R10 rifle-only angle calibration

The owner confirms r9 is installed and has manually set `g_gunX -4`,
`g_gunY 4`, `g_gunZ 1`. Their larger image also demonstrates that the earlier
close view was cropped. Do not use the cropped panel center as the center in a
full viewport. Scale and active weapon FOV were requested but not confirmed
when this rotation trial was prepared. The previous translation estimate was
conditional, not a measured host pose.

R10 retains r9's model offset and all global gun values. It adds a small
`(pitch=0, yaw=0, roll=-3)` trial and independent rifle angle controls to the
existing `ReachApplyViewPose` method. This roll is an authoring trial to
slightly flatten the receiver and change the panel's lean, not a recovered
Reach retail constant or an exact screenshot solve. A calibrated six-axis fit
still requires corresponding landmarks at compatible aspect ratios.

The pivot is the original converted idle counter's model-space center
`P=(15.84341446,-4.47929218,0.28925242)`. The transform is
`R * (point - P) + P`, implemented as an additive root orientation and
translation `P - R*P`. The counter center stays fixed, independent of uniform
gun scale, offsets or projection. BFG's right vector is negative model Y;
the script uses `Forward*P.x - Right*P.y + Up*P.z` to obtain `R*P`.

Use `JOINTMOD_WORLD` for the axis, preserving the donor's 90-degree root roll.
Use `JOINTMOD_LOCAL` for position because the root's WORLD position branch
overrides its animation value. All child joints, hands, clips and muzzle
markers inherit the same rigid correction. No mesh, weight or clip is rewritten.
Apply on initialization and Raise; do not add frame polling or alter weapon
states, object fields, projectile code, input controls or the projection tag.

An unset `reach_arPitch/Yaw/Roll` uses the trial defaults. Set all three to
zero and reselect the rifle to compare with the original r9 pose. `seta` can
retain owner tuning through the normal engine config. Script bytecode changes
can invalidate earlier saves: use a fresh map for the first check.

The r10 package replaces the same six-z `zzzzzz_reach_position.pk4`, containing
the unchanged r9 declaration and the weapon script with only that presentation
method replaced. The five-z r8 projection overlay remains installed. Neither
the executable nor any config/launcher/material/asset file is shipped.

```sh
python tools/reach/position/test_pose.py
python tools/reach/position/build_pose.py /tmp/Reach-rifle-pose-r10.zip
```

Checks use the engine's actual angle-axis expressions and root modifier
branches, test pivot preservation and rigid distances, verify existing event
types, and compare all other script state bodies and object fields with r8.
Package checks verify exact override paths, CRCs and overwrite preservation.
These are not a script compile or a running-game validation; owner testing
is still required. The lightweight Windows workflow publishes the pose ZIP
without recompiling the accepted r8 executable.
