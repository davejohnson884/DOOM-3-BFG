Position-only update for the accepted r8 projection

The owner accepted the rifle's apparent perspective and reported that the rig
was too close and too central. Preserve `ReachRBDoom3BFG.exe`, weapon FOV 54 and
all r8 code, scripts, materials, controls and original donor clips.

`build_position.py` adds a higher-priority PK4 containing only
`def/reach_presentation.def`. Reuse that virtual filename: a differently named
file declaring the same model can introduce a duplicate declaration instead
of overriding the original through the filesystem. The inherited model's
visual offset moves the complete rig and its muzzle joint together.

The r9 offset is `(4, -4.2, -2.8)`, a translation of `(7, -4.2, -1.6)` from
r8. This is a relative fit from the owner's latest screenshot, using the ammo
panel's height and center against the full-frame Reach 360 reference. It does
not assume that a narrower weapon FOV alone places the authored rig correctly.
The original Reach camera constant has not been recovered.

The approximate panel height is 26% of the latest frame versus 14% in the
reference; its center is around `(0.52, 0.43)` versus `(0.70, 0.60)`. These are
visual estimates from chat images, not pixel measurements or a calibrated
camera solve. At the unchanged projection and unit gun scale, the converted
idle panel's known height supports roughly seven BFG units of added depth,
with a right/down correction. Saved gun offsets and actual screenshot cropping
remain unmeasured. Owner comparison is required; do not claim exact parity.

Build with Python 3.12 (standard library only):

```sh
python tools/reach/position/build_position.py /tmp/Reach-rifle-position-r9.zip
```

The packager checks ZIP CRCs and that merging its virtual files into r8 changes
only the model declaration. It includes no executable or private game content.
Its separate packaging workflow avoids recompiling the accepted engine for a
declaration-only change. Remove the added PK4 to return to r8 positioning.
