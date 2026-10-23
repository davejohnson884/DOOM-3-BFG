# Opt-in Reach projection on the released RBDoom foundation

Target: the owner's `RBDOOM-3-BFG-1.6.0.22-full-win64-20250510-git-ba39ba6`,
upstream source `ba39ba67df049dcf16c7b31f6613f72959be2c21` and its pinned
submodules. This is a separate executable candidate, not a gameplay DLL or
proxy/injection hook. Published RBDoom compiles gameplay into the executable;
the `__DOOM_DLL__` loader branch is not enabled in its normal build.

`r_reachWeaponFov` defaults to 0 without archive persistence. Positive values
select horizontal weapon FOV referenced to 4:3. Scope also requires the exact
rifle/flash model name, shader parm 6 equal to 1, a weapon depth hack, and the
matching owner's first-person view. Mirrors/subviews and ordinary entities
retain the original projection path. Parm 6 is used only as an opt-in marker
for this content; counter controls remain in parms 9 and 10.

The projection helper replaces two focal coefficients in copies of the
regular and unjittered projection. It preserves clipping, jitter and depth
terms, and keeps model/physics transforms orthonormal. Ambient, counter,
depth and interaction draws use the same entity MVP. The selected model's
portal/light scissor is broadened for its different projection, then restored
for ordinary interaction spaces. First-person motion-blur masking avoids
using world-camera velocity for the modified entity. This does not alter
renderer options, job scheduling or other host defaults.

The script removes r7's extra root rotation, tags the model and uses offset
`(-3,0,-1.2)`: cancel the host's default +3 forward offset and use the decoded
Reach centered vertical offset. It does not deform any mesh/animation. The
initial 54-degree weapon FOV is a real public MA37 SWEP setting, not a recovered
Reach retail constant. Runtime pose/scale fidelity remains unverified.

After the candidate script constructor tags the rifle, the native weapon
creates an owned `func_emitter` with the existing authored flash declaration,
owner view restriction, projection marker and `cycleTrigger`. It reuses
the stock weapon-particle attachment/save paths and starts the flash only
after an actual projectile launch. This avoids the shared smoke geometry's
world projection. The standard shared flash is disabled for that tagged
rifle only. No game assets/stock definitions are copied into the public patch.

`apply_rbdoom.py` requires the exact source revision and untouched versions
of its four target source files. It validates every anchor before writing.
It adds a helper header and a frame-local boolean in `viewEntity_t`, without
changing public entity interfaces or serialization layouts. Modified script
save compatibility is still unverified; first owner tests use a fresh map.

Build on Windows using VS2022 x64 tools and CMake 3.31.6:

```text
git clone --branch v1.6.0 --recursive https://github.com/RobertBeckebans/RBDOOM-3-BFG.git rbdoom
python tools/reach/native/apply_rbdoom.py rbdoom
powershell -File tools/reach/native/prepare-build.ps1 -Source rbdoom -Dependencies build/deps
cmake --build rbdoom/build-reach --config Release --target RBDoom3BFG --parallel 4
```

Preparation pins/checksums official DXC/ISPC archives and Khronos Vulkan
exports, uses the release's pinned Vulkan headers, and builds a standard
Win64 Vulkan import library locally. It configures the normal Win64 DX12
and Vulkan backends with XAudio2 and libbinkdec. These are build tools, not a
PowerShell play harness or replacement runtime SDK/DLLs. The candidate reuses
the owner's published shader/support files.

The GitHub workflow `reach-rbdoom-native.yml` compiles the camera/scope tests,
builds/links the actual engine, verifies the existing Windows debug reader,
and checks direct/diagnostic candidate launchers with a fixture. The package
contains a renamed engine, authored script/material overlay, licenses, patch,
source helper and reproducibility manifest. The private rifle archive must
already be installed. See `PLAYER-README.txt` for installing/removing it.

Full engine compilation and these checks do not execute the game or establish
graphics correctness, stability or original Reach parity. V input diagnosis
and G grenade integration are separate unfinished work.


## Reach animation camera

The opted-in single-player Reach AR now evaluates the existing camera_control joint in parent-local space for melee, grenade throws and the sprint loop. This cancels the accepted viewmodel root placement. Reload, empty reload, ready/raise, lower and sprint transitions use bounded camera-specific curves keyed to the native animation clock. Firing adds a short impulse for each actual projectile launch, with finite recovery and a small deterministic alternating side component.

GetViewPos applies the transient local transform to the same frame used by the camera and first-person weapon. It never writes input viewAngles. The camera tracks action blends, clears on weapon Clear, and resets on clock rewind; repeated view queries at one simulation time cannot integrate twice. Camera offsets are limited to two host units and 6 degrees per axis. Multiplayer, spectator, cinematic, private-camera and third-person paths retain the original view calculation. Existing walking/landing camera behavior is retained; the old Doom weapon sway remains bypassed for the tagged rifle.

CameraMotion.h is independent of engine types. test_camera.cpp checks finite shot recovery, action endpoints, duplicate-query safety, frame-rate-independent settling, interruption recovery, clock reset and bounds. check_combat.py strips both guarded player insertions and verifies the remaining player source is byte-identical to the pinned release. reach_cameraDebug is an optional non-archived diagnostic switch; off by default. No private Reach assets or renderer/performance/thread/display changes are needed for this extension. The transient camera state is deliberately not added to the save format and initializes cleanly when a weapon is constructed/restored.


Camera strength refinement: firing and reload gains default to 2.5, sprint and melee to 2.8 relative to the first camera pass. Ready/raise, lower, grenade throw and existing walking camera retain their prior behavior. The non-archived runtime controls `reach_cameraFireScale`, `reach_cameraReloadScale`, `reach_cameraSprintScale`, `reach_cameraMeleeScale` accept 0–4. The stronger melee retains source timing and direction; the output angle safety bound is now 6 degrees, with the existing two-unit position bound. No new scripts, assets, serialization or input view-angle changes.
