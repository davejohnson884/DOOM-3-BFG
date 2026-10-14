# Reach rifle projection investigation

The owner rejected r7: its camera pullback overshot, and the receiver/counter
still have the wrong apparent perspective. Treat r7 as an unsuccessful pose
candidate. Passing package tests and a rigid-transform audit did not validate
its appearance in the game.

Halo 3 is a useful reference for Reach because both belong to the Blam engine
family. Shared ancestry does not establish identical camera constants. The
specific comparison pack is Steam Workshop item **1981371407**; the owner
reports that its scale and apparent perspective closely match Halo 3.

## Recovered previous fix

The owner's public `davejohnson884/DOOM-3` project contains the implementation
that previously solved their Quake 4 weapon presentation. At commit
`a5884d45c42c6f8d8afe60385da651d5e4e8bdb1` on
`q4bse-v21-core-renderer-parity`,
`q4bse_port/apply_q4_viewmodel_presentation.py` patches `PresentWeapon` to:

1. Add the definition's `viewoffset` in the current weapon basis.
2. Compose its `viewangles` with the existing orientation.
3. Multiply **only `renderEntity.axis[0]`** by `foreshorten`.
4. Submit the entity, then restore the original origin and axis.

That is a render-time forward-axis compression, in addition to pose changes.
The script documents the earlier V108/V110 hook as its reference. The source
integrated version is compiled into the original Doom 3 gameplay DLL. It does
not establish a Reach compression factor, and the DLL is not a compatible
RBDoom3BFG module.

[Previous implementation](https://github.com/davejohnson884/DOOM-3/blob/a5884d45c42c6f8d8afe60385da651d5e4e8bdb1/q4bse_port/apply_q4_viewmodel_presentation.py)

## Actual Halo and SWEP evidence

| Source | Verified mechanism | Limit |
| --- | --- | --- |
| ChimpsAtSea/Reach, `8723dc3d051a29675e00ffe3f8eebf355a30a702` | `c_first_person_view::m_fov_scale`, `override_projection`, `set_camera_squish_ratio`, and related squish symbols | Work-in-progress reconstruction of a 2011 Xbox 360 tag-debug build; the relevant function bodies are stubs. No original Reach numeric projection has been recovered. |
| twist84/ManagedDonkey, `65eb5b2aafac16ebb33f213c1286eda5fa1e4446` | Implemented first-person projection override modifies camera FOV and rebuilds projection; optional squish changes near/far camera parameters | Its README targets **Halo Online ms23**, derived from the Halo 3 family. Its `0.6908` factor is not verified as an original Halo 3 Xbox 360 or Reach constant. |
| NimaBullock/DTHRPAssets, `f129e6e84a4764b024f71a2189ec721f4b7a6ec8`, `ma37.lua` | A real Reach MA37 SWEP sets `ViewModelFOV = 54`, `VMPos = Vector(0, 0, -1)`, and zero `VMAng` | The README identifies modified MCC models. This is not verified as Workshop item 1981371407, and the compiled model's baked transforms have not been examined. |
| SnowySnowtime/haloceweapons, `ecee36a1f1f277b39d32bef63267bf26b2d7418b` | Its Halo 3 rifle sets `ViewModelFOV = 70` and `ActivePos = Vector(0, -2, 0)` | Another public port, not a verified match for the owner's linked pack. Different ports use different camera/model combinations. |

[Reach first-person symbols](https://github.com/ChimpsAtSea/Reach/blob/8723dc3d051a29675e00ffe3f8eebf355a30a702/src/source/omaha/render/views/render_first_person_view.cpp)
· [Halo Online projection implementation](https://github.com/twist84/ManagedDonkey/blob/65eb5b2aafac16ebb33f213c1286eda5fa1e4446/game/source/render/views/render_view.cpp)
· [MA37 SWEP](https://github.com/NimaBullock/DTHRPAssets/blob/f129e6e84a4764b024f71a2189ec721f4b7a6ec8/Weapons/lua/weapons/ma37.lua)
· [MA37 asset provenance](https://github.com/NimaBullock/DTHRPAssets/blob/f129e6e84a4764b024f71a2189ec721f4b7a6ec8/Weapons/README.md)
· [Other Halo 3 rifle](https://github.com/SnowySnowtime/haloceweapons/blob/ecee36a1f1f277b39d32bef63267bf26b2d7418b/lua/weapons/arccw_h3_snow_vuth_ar.lua)

Steam Workshop access was denied by this environment's network proxy. Public
GitHub source and repository searches were available, with search later rate
limited. Searches did not identify a source mirror for item 1981371407. Do
not claim its title, author, code, screenshots, or FOV were inspected.

## Camera conventions matter

Valve's Source SDK `view.cpp` scales the weapon FOV using the display aspect
relative to 4:3, independently of world FOV. Under that convention, a 54-degree
reference horizontal weapon FOV corresponds to approximately:

| Layout | Horizontal FOV | Vertical FOV |
| --- | --- | --- |
| 4:3 | 54.00 degrees | 41.83 degrees |
| 16:9 | 68.38 degrees | 41.83 degrees |
| 3440x1440 | 84.79 degrees | 41.83 degrees |

These are calculated camera-convention examples, not measurements of Reach,
GMod's current runtime, or the owner's BFG weapon camera. Copying `54` into
the world `g_fov` would not reproduce the SWEP's separate projection. Preserve
the owner's world FOV of 100 and use 16:9 as the framing reference.

[Source SDK FOV handling](https://github.com/ValveSoftware/source-sdk-2013/blob/be57e3d01ac7d7aa6a2cacbfef187c0b46616db0/src/game/client/view.cpp)

## Released RBDoom3BFG boundary

Inspected release `v1.6.0`, source commit
`ba39ba67df049dcf16c7b31f6613f72959be2c21`, against the owner's reported
`1.6.0.1403` host:

- The model MVP is formed using the view's projection. There is no verified
  exposed per-weapon FOV or forward-axis scale in the weapon script interface.
- `ApplyDepthHack` multiplies only the projected Z row by 0.25. X, Y and W are
  unchanged. This prevents wall intersection; it does not compress the visible
  receiver or set a weapon FOV.
- Root rotation and definition offsets change pose. They cannot supply an
  independent projection parameter.
- The MD5 animation representation contains rotation and translation, without
  scale channels. The release's glTF importer also converts bone poses to
  rotation/translation and explicitly marks animation scale unsupported.
  Simply scaling a root nonuniformly in Blender is not a verified way to
  preserve the current reload, sprint, melee and attachment animation.
- Custom material programs exist, but a custom ambient stage alone does not
  establish matching skinning, depth, lighting and counter passes. Replacing
  built-in shaders is not an established correction route.

[RBDoom entity MVP setup](https://github.com/RobertBeckebans/RBDOOM-3-BFG/blob/ba39ba67df049dcf16c7b31f6613f72959be2c21/neo/renderer/tr_frontend_addmodels.cpp)
· [Depth hack](https://github.com/RobertBeckebans/RBDOOM-3-BFG/blob/ba39ba67df049dcf16c7b31f6613f72959be2c21/neo/idlib/geometry/RenderMatrix.h)
· [glTF skeletal conversion](https://github.com/RobertBeckebans/RBDOOM-3-BFG/blob/ba39ba67df049dcf16c7b31f6613f72959be2c21/neo/renderer/Model_gltf.cpp)

## Correction specification

A native route, if selected, should add an opt-in weapon-only projection to
the **released RBDoom foundation**, defaulting to the existing behavior. It
must leave world projection, other weapons, physics/aim, renderer settings,
display selection, threading and job scheduling at the port's defaults.
Its projection must agree across the lit rifle, counter, depth and temporal
passes, with visible muzzle effects attached to the corresponding apparent
position. RBDoom documents a renamed executable for native modifications;
copying the old Quake 4 project's gameplay DLL is not supported.

The public MA37 SWEP's camera is a concrete comparison candidate, not an
established original Reach preset. Calibrate full pose with the independent
projection using counter corners, receiver, muzzle, stock and both hands.
Verify idle, firing, reload, sprint and melee at 16:9, then ultrawide. A match
at a single landmark or a successful package test is insufficient.

No new executable, shader replacement, mesh deformation or offset patch was
produced by this investigation. Exact linked-pack parameters and original
Reach projection constants remain unresolved. V input still requires its
existing runtime trace; G grenade integration remains separate unfinished
work.
