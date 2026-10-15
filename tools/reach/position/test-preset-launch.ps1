$ErrorActionPreference = 'Stop'
try {
$fixtureRoot = Join-Path $env:RUNNER_TEMP ('Reach Preset Launch ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null
Expand-Archive -LiteralPath build/Reach-rifle-preset-r12.zip -DestinationPath $fixtureRoot
$env:REACH_PRESET_FIXTURE_ROOT = $fixtureRoot
@'
import io, os, sys, zipfile
from pathlib import Path
sys.path.insert(0, 'tools/reach/native')
import build_candidate
sys.path.insert(0, 'tools/reach/position')
import build_preset
import build_pose
root = Path(os.environ['REACH_PRESET_FIXTURE_ROOT'])
(root/'reach/zzzzz_reach_projection.pk4').write_bytes(build_candidate.overlay())
(root/'reach/zzz_reach_ar.pk4').write_text('asset fixture only')
old = io.BytesIO()
with zipfile.ZipFile(old, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('script/weapon_machinegun.script', build_pose.script())
    archive.writestr('def/reach_presentation.def', build_pose.DECLARATION)
(root/'reach/zzzzzz_reach_position.pk4').write_bytes(old.getvalue())
with zipfile.ZipFile(root/build_preset.PK4_PATH) as archive:
    assert archive.testzip() is None
    assert archive.read('script/weapon_machinegun.script') == build_preset.script()
    assert archive.read('def/reach_presentation.def') == build_preset.DECLARATION
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'Installed package or rifle-only script check failed.' }

$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$captureOutput = Join-Path (Get-Location) 'build/ReachDebugLog.exe'
$captureSource = Join-Path (Get-Location) 'tools/reach/rbdoom/ReachDebugLog.cs'
$captureCompilerOutput = @(& $compiler /nologo /platform:x64 /target:exe ('/out:' + $captureOutput) $captureSource 2>&1)
if ($LASTEXITCODE -ne 0) {
    $details = ($captureCompilerOutput -join ' ').Replace('%', '%25')
    Write-Host "::error title=Preset helper compiler::$details"
    throw 'Existing diagnostic helper compilation failed.'
}
Copy-Item -LiteralPath $captureOutput -Destination (Join-Path $fixtureRoot 'ReachDebugLog.exe')
$fixtureCode = Join-Path (Get-Location) 'build/preset-fixture.cs'
@'
using System;
using System.IO;
using System.IO.Compression;
using System.Collections.Generic;

// This command/config fixture is not the game. It checks actual CMD argv,
// nested config selection and applied values starting from stale settings.
public static class PresetFixture {
    static string root = AppDomain.CurrentDomain.BaseDirectory;
    static Dictionary<string, string> vars = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase) {
        {"g_gunX","-4"}, {"g_gunY","4"}, {"g_gunZ","1"},
        {"reach_arPitch","9"}, {"reach_arYaw","9"}, {"reach_arRoll","0"},
        {"g_gunScale","0.7"}, {"g_fov","100"}, {"r_fullscreen","1"}, {"jobs_numThreads","8"}
    };
    static Dictionary<string, string> defaults = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase) {
        {"g_gunX","3"}, {"g_gunY","0"}, {"g_gunZ","0"}
    };
    static string ReadConfig(string name) {
        string loose = Path.Combine(root, "reach", name);
        if (File.Exists(loose)) return File.ReadAllText(loose);
        // Published RBDoom sorts PK4 names, then searches in reverse order.
        string[] archives = Directory.GetFiles(Path.Combine(root, "reach"), "*.pk4");
        // idStr::IcmpPath folds ASCII to lowercase. OrdinalIgnoreCase folds
        // to uppercase, which orders '_' after 'Z' and reverses these names.
        Array.Sort(archives, delegate(string a, string b) {
            return StringComparer.Ordinal.Compare(a.ToLowerInvariant(), b.ToLowerInvariant());
        });
        for (int i = archives.Length - 1; i >= 0; --i) {
            using (var archive = ZipFile.OpenRead(archives[i])) {
                var entry = archive.GetEntry(name);
                if (entry != null) using (var reader = new StreamReader(entry.Open())) return reader.ReadToEnd();
            }
        }
        throw new FileNotFoundException("Config not installed: " + name);
    }
    static void Exec(string name, int depth) {
        if (depth > 10) throw new Exception("Config recursion");
        foreach (string raw in ReadConfig(name).Split('\n')) {
            string line = raw.Trim();
            if (line.Length == 0 || line.StartsWith("//")) continue;
            string[] parts = line.Split(new char[] {' ', '\t'}, 3, StringSplitOptions.RemoveEmptyEntries);
            if (parts[0] == "exec") Exec(parts[1], depth + 1);
            else if (parts[0] == "reset") vars[parts[1]] = defaults[parts[1]];
            else if (parts[0] == "set" || parts[0] == "seta") vars[parts[1]] = parts[2].Trim('"');
        }
    }
    public static int Main(string[] args) {
        try {
            File.WriteAllText(Path.Combine(root, "arguments.txt"), Environment.CurrentDirectory + "\n" + String.Join("\n", args));
            if (!ReadConfig("script/weapon_machinegun.script").Contains("r12 rifle anchor")) throw new Exception("Old overlay won script priority");
            for (int i = 0; i < args.Length; ++i) {
                if (args[i] == "+exec") Exec(args[++i], 0);
                else if (args[i] == "+set") { string name = args[++i]; vars[name] = args[++i]; }
            }
            string[] names = {"g_gunX","g_gunY","g_gunZ","reach_arGunX","reach_arGunY","reach_arGunZ","reach_arPitch","reach_arYaw","reach_arRoll","g_gunScale","g_fov","r_fullscreen","jobs_numThreads","r_reachWeaponFov"};
            var result = new List<string>();
            foreach (string name in names) result.Add(name + "=" + vars[name]);
            File.WriteAllLines(Path.Combine(root, "settings.txt"), result.ToArray());
            return 0;
        } catch (Exception error) {
            File.WriteAllText(Path.Combine(root, "fixture-error.txt"), error.ToString());
            return 1;
        }
    }
}
'@ | Set-Content -LiteralPath $fixtureCode
$fixtureOutput = Join-Path (Get-Location) 'build/ReachPresetFixture.exe'
$fixtureCompilerOutput = @(& $compiler /nologo /platform:x64 /target:exe /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll ('/out:' + $fixtureOutput) $fixtureCode 2>&1)
if ($LASTEXITCODE -ne 0) {
    $details = ($fixtureCompilerOutput -join ' ').Replace('%', '%25')
    Write-Host "::error title=Preset game fixture compiler::$details"
    throw 'CMD/config fixture compilation failed.'
}
Copy-Item -LiteralPath $fixtureOutput -Destination (Join-Path $fixtureRoot 'ReachRBDoom3BFG.exe')

$settings = Join-Path $fixtureRoot 'settings.txt'
$arguments = Join-Path $fixtureRoot 'arguments.txt'
$expectedSettings = @('g_gunX=3', 'g_gunY=0', 'g_gunZ=0', 'reach_arGunX=-4', 'reach_arGunY=4', 'reach_arGunZ=1', 'reach_arPitch=0', 'reach_arYaw=0', 'reach_arRoll=-3', 'g_gunScale=0.7', 'g_fov=100', 'r_fullscreen=1', 'jobs_numThreads=8', 'r_reachWeaponFov=54')
foreach ($diagnostic in @($false, $true)) {
    $name = if ($diagnostic) { 'Play-Reach-projection-diagnostic.cmd' } else { 'Play-Reach-projection.cmd' }
    $command = '"' + (Join-Path $fixtureRoot $name) + '"'
    if ($diagnostic) { $command += ' --no-explorer' }
    & cmd.exe /d /c $command
    if ($LASTEXITCODE -ne 0) { throw 'Packaged CMD failed.' }
    $deadline = (Get-Date).AddSeconds(10)
    while (-not (Test-Path -LiteralPath $settings) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path -LiteralPath $settings)) { throw 'Fixture did not execute the preset.' }
    if (@(Compare-Object $expectedSettings (Get-Content -LiteralPath $settings)).Count -ne 0) { throw 'Preset did not apply the requested values or changed unrelated settings.' }
    $expectedArgs = @($fixtureRoot, '+set', 'fs_game', 'reach')
    if ($diagnostic) { $expectedArgs += @('+set', 'logFileName', (Join-Path $env:TEMP 'Reach-weapon-switch.log'), '+set', 'logFile', '2', '+set', 'g_debugWeapon', '1') }
    $expectedArgs += @('+exec', 'reach_pose.cfg')
    if ((Get-Content -Raw -LiteralPath $arguments) -ne ($expectedArgs -join [char]10)) { throw 'Packaged CMD selected the wrong config, executable directory or arguments.' }
    Remove-Item -LiteralPath $settings, $arguments
}

# An incomplete copy must stop, not silently launch the previous preset.
Remove-Item -LiteralPath (Join-Path $fixtureRoot 'reach/reach_pose.cfg')
& cmd.exe /d /c ('"' + (Join-Path $fixtureRoot 'Play-Reach-projection.cmd') + '" <nul')
if ($LASTEXITCODE -ne 1 -or (Test-Path -LiteralPath $arguments)) { throw 'Missing preset was not rejected before launch.' }
Write-Host '::notice title=Rifle-only Reach preset::PASS: both packaged CMD files restore stock global offsets and load rifle-only -4/4/1 and 0/0/-3; scale/world-FOV/display/thread fixture values retained; missing preset rejected.'
} catch {
    $message = ($_.Exception.Message + ' ' + $_.InvocationInfo.PositionMessage).Replace('%', '%25').Replace([string][char]13, '%0D').Replace([string][char]10, '%0A')
    Write-Host "::error title=Preset launch check::$message"
    if ($fixtureRoot -and (Test-Path -LiteralPath (Join-Path $fixtureRoot 'fixture-error.txt'))) {
        $details = (Get-Content -Raw -LiteralPath (Join-Path $fixtureRoot 'fixture-error.txt')).Replace('%', '%25').Replace([string][char]13, '%0D').Replace([string][char]10, '%0A')
        Write-Host "::error title=Preset fixture::$details"
    }
    exit 1
}
exit 0
