# Reach combat project

Target: Halo Reach combat inside Steam Doom 3 BFG, using the owner's Steam MCC Reach installation as the asset source. First milestone: one assault rifle, quick weapon melee, independent frag throw, and sprint. Gameplay is reimplemented in BFG; this is not running the Halo engine inside Doom.

## Current status

Development branch: `reach-combat`. The Windows workflow is an initial baseline build attempt using MSVC v143 and the authenticated Microsoft DirectX June 2010 SDK download. The original source targets Visual Studio 2010; compatibility with the hosted compiler is **not yet verified**. Compilation does not prove in-game readiness. No converted Halo assets or working Reach weapons are included yet.

The workflow keeps the SDK installation out of the checkout, verifies the SDK installer's Microsoft signature before extraction, and uploads logs even when the build fails. A successful build uploads `reach-bfg-win32`; do not replace your Steam executable yet. A backed-up lab installation and runtime smoke test come first.

## Runtime and assets

The cloud machine cannot access your PC's Steam folders. Record the install paths for Doom 3 BFG and MCC using Steam Properties → Installed Files → Browse. Reach extraction must first be validated against those files. The existing Universal Modder Halo 3/Minecraft example is a useful reference, but does not establish that Reach first-person animations can be exported or converted.

Confirmed installs: BFG at `C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition`; MCC at `D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection`. Download this branch as a ZIP and extract it outside your Steam folders. Open `tools/reach` and double-click `Collect-install-info.cmd`. It creates a uniquely named JSON report containing file names, sizes and executable versions. It reads the game folders and changes no game files. Send the report to the project chat. The launcher's execution policy override is scoped to that one process; it does not change your Windows execution-policy settings.

Keep extracted models, textures, sounds and animations outside Git. The intended distribution is source code, build artifacts and a local conversion tool; donor game data stays on the owner's PC. The first functional prototype should use BFG assets to validate controls and action timing before importing the Reach presentation.

Combat integration points: `neo/d3xp/Player.cpp` (`Weapon_Combat`, `PerformImpulse`, `AdjustSpeed`), `neo/d3xp/Weapon.cpp` (animation, melee and projectile events), and `neo/framework/UsercmdGen.h` (inputs). Script and weapon definitions live in installed game data and must be inspected before authoring replacements.
