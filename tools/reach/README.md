# Reach combat project

Target: Halo Reach combat inside Steam Doom 3 BFG, using the owner's Steam MCC Reach installation as the asset source. First milestone: one assault rifle, quick weapon melee, independent frag throw, and sprint. Gameplay is reimplemented in BFG; this is not running the Halo engine inside Doom.

## Current status

Development branch: `reach-combat`. An opt-in sprint prototype is implemented: forward-only grounded sprint, weapon lowering, interruption on fire/zoom/reload, firing suppression during sprint and recovery, and a minimum charge to restart. Stock mode and multiplayer use the original running path. Sprint/recovery state resets on loading a save; existing serialized stamina is retained. No converted Halo assets or working Reach weapons are included yet.

The isolated sprint state-machine scenarios pass under GCC in C++98 mode. They check interruption/recovery, charge exhaustion, restart gating and reset behavior; they do not validate player physics, animations or game startup. The Windows workflow uses MSVC v143 and a signature-verified Microsoft DirectX June 2010 SDK download. The original source targets Visual Studio 2010; compatibility with the hosted compiler is **not yet verified**. Compilation does not prove in-game readiness.

`reach-prototype.cfg` contains initial tuning, not authentic Reach stats. Apply it only in a backed-up lab once a compiled executable is verified. Launch-time `+set g_reachCombat 0` disables the prototype; remove the prototype config and restore your original movement/bind settings to restore the full stock configuration. Accurate Reach sprint speed, charge and recovery timing still require donor-data inspection or measurements.

The workflow keeps the SDK installation out of the checkout, verifies the SDK installer's Microsoft signature before extraction, and uploads logs even when the build fails. A successful build uploads `reach-bfg-win32`; do not replace your Steam executable yet. A backed-up lab installation and runtime smoke test come first.

The modern compiler adapter keeps the original warning level and diagnostics, but does not promote legacy warnings to errors. The original source predates MSVC warnings about member shadowing, specialization storage classes and inline allocation operators. Actual compiler/linker errors still fail the workflow, and the isolated sprint tests use warnings as errors. Source compatibility changes retain the VS2010 annotation path and use SAL on modern MSVC.

## Runtime and assets

The cloud machine cannot access your PC's Steam folders. Record the install paths for Doom 3 BFG and MCC using Steam Properties → Installed Files → Browse. Reach extraction must first be validated against those files. The existing Universal Modder Halo 3/Minecraft example is a useful reference, but does not establish that Reach first-person animations can be exported or converted.

Confirmed installs: BFG at `C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition`; MCC at `D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection`. Download this branch as a ZIP and extract it outside your Steam folders. Open `tools/reach` and double-click `Collect-install-info.cmd`. It creates a uniquely named JSON report containing file names, sizes and executable versions. It reads the game folders and changes no game files. Send the report to the project chat. The launcher's execution policy override is scoped to that one process; it does not change your Windows execution-policy settings.

Keep extracted models, textures, sounds and animations outside Git. The intended distribution is source code, build artifacts and a local conversion tool; donor game data stays on the owner's PC. The first functional prototype should use BFG assets to validate controls and action timing before importing the Reach presentation.

Combat integration points: `neo/d3xp/Player.cpp` (`Weapon_Combat`, `PerformImpulse`, `AdjustSpeed`), `neo/d3xp/Weapon.cpp` (animation, melee and projectile events), and `neo/framework/UsercmdGen.h` (inputs). Script and weapon definitions live in installed game data and must be inspected before authoring replacements.
