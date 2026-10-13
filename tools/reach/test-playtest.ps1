$ErrorActionPreference = 'Stop'
$testRoot = Join-Path $env:RUNNER_TEMP ('reach-launch-test-' + [Guid]::NewGuid().ToString('N'))
$package = Join-Path $testRoot 'Package'
$bfg = Join-Path $testRoot 'Steam BFG'
$saved = Join-Path $testRoot 'Saved Games'
$original = Join-Path $saved 'id Software/DOOM 3 BFG'
New-Item -ItemType Directory -Path $package, (Join-Path $bfg 'base'), $original -Force | Out-Null
Set-Content (Join-Path $bfg 'base/_common.resources') 'fixture'
Set-Content (Join-Path $bfg 'base/_ordered.resources') 'fixture'
Set-Content (Join-Path $original 'existing-save.txt') 'preserve this profile'
Copy-Item (Join-Path $PSScriptRoot 'start-playtest.ps1') $package
Copy-Item (Join-Path $PSScriptRoot 'reach_prototype.cfg') $package
$binary = Join-Path $package 'Doom3BFG.exe'
Set-Content $binary 'fixture; must never be launched'
@{ sha256 = (Get-FileHash $binary -Algorithm SHA256).Hash } | ConvertTo-Json |
    Set-Content (Join-Path $package 'build-sha256.json')
$result = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw ('Lab preparation failed: ' + ($result -join ' ')) }
$session = @(Get-ChildItem $package -Directory -Filter 'playtest-*')
if ($session.Count -ne 1) { throw 'Expected one isolated playtest session.' }
$plan = Get-Content (Join-Path $session[0].FullName 'launch-plan.json') -Raw | ConvertFrom-Json
if (-not $plan.profile.StartsWith($session[0].FullName) -or $plan.arguments -notmatch '\+set fs_game reach_lab') {
    throw 'The launch plan did not isolate its profile/mod directory.'
}
if ($plan.arguments -notmatch '\+set r_fullscreen -1\b' -or
    $plan.arguments -notmatch '\+set r_windowWidth ([1-9][0-9]*)\b' -or
    $plan.arguments -notmatch '\+set r_windowHeight ([1-9][0-9]*)\b' -or
    $plan.arguments -notmatch '\+set logFile 1\b' -or
    $plan.arguments -notmatch '\+set logFileName "[^"\r\n]+qconsole\.log"' -or
    $plan.arguments -notmatch '\+set com_timestampPrints 1\b') {
    throw 'Normal playtests must cover the desktop and use timestamped, buffered logging.'
}
$mod = Join-Path $plan.profile 'reach_lab'
if (-not (Test-Path (Join-Path $mod 'reach_prototype.cfg')) -or
    @(Get-Content (Join-Path $mod 'autoexec.cfg')) -notcontains 'exec reach_prototype.cfg' -or
    $plan.arguments -notmatch '\+set g_reachLabAutoConfig 1') {
    throw 'The lab configuration was not staged for startup and post-spawn loading.'
}
$backupFile = Join-Path $session[0].FullName 'backup-original-profile/existing-save.txt'
if ((Get-Content $backupFile -Raw).Trim() -ne 'preserve this profile' -or
    (Get-Content (Join-Path $original 'existing-save.txt') -Raw).Trim() -ne 'preserve this profile') {
    throw 'The original profile was not preserved and backed up.'
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -Windowed -FlushLog -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Explicit windowed/flush-log preparation failed.' }
$sessions = @(Get-ChildItem $package -Directory -Filter 'playtest-*')
if ($sessions.Count -ne 2) { throw 'Expected a separate session for the explicit windowed launch.' }
$windowedSession = @($sessions | Where-Object { $_.FullName -ne $session[0].FullName })[0]
$windowedPlan = Get-Content (Join-Path $windowedSession.FullName 'launch-plan.json') -Raw | ConvertFrom-Json
if ($windowedPlan.arguments -notmatch '\+set r_fullscreen 0\b' -or
    $windowedPlan.arguments -notmatch '\+set r_windowWidth 1280\b' -or
    $windowedPlan.arguments -notmatch '\+set logFile 2\b') {
    throw 'Explicit windowed/flush-log options were ignored.'
}
foreach ($variant in @('single-threaded', 'stock-combat')) {
    $options = if ($variant -eq 'single-threaded') { @('-SingleThreaded', '-Diagnostics') } else { @('-StockCombat', '-Diagnostics') }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -Windowed -PrepareOnly @options
    if ($LASTEXITCODE -ne 0) { throw "Failed to prepare $variant comparison." }
    $plans = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object {
        Get-Content (Join-Path $_.FullName 'launch-plan.json') -Raw | ConvertFrom-Json
    })
    $comparison = @($plans | Where-Object { if ($variant -eq 'single-threaded') { $_.threading -eq $variant } else { $_.mode -eq $variant } })[0]
    if ($null -eq $comparison -or $comparison.arguments -notmatch '\+set com_reachDiagnostics 1\b') { throw 'Diagnostic comparison is missing.' }
    if ($variant -eq 'single-threaded') {
        foreach ($setting in @('com_smp', 'jobs_numThreads', 'r_useParallelAddModels', 'r_useParallelAddLights', 'r_useParallelAddShadows')) {
            if ($comparison.arguments -notmatch ('\+set ' + $setting + ' 0\b')) { throw "Comparison did not disable $setting." }
        }
        if ($comparison.arguments -notmatch '\+set g_reachCombat 1\b') { throw 'Single-thread comparison lost Reach combat.' }
    } else {
        $baselineConfig = Get-Content (Join-Path $comparison.profile 'reach_lab/autoexec.cfg') -Raw
        if ($comparison.arguments -notmatch '\+set g_reachCombat 0\b' -or
            $comparison.arguments -notmatch '\+set g_reachLabAutoConfig 0\b' -or
            $comparison.arguments -match '\+exec reach_prototype' -or $baselineConfig -match 'exec reach_prototype') {
            throw 'Stock comparison could re-enable Reach tuning/bindings.'
        }
    }
}
Set-Content $binary 'modified fixture'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -PrepareOnly
if ($LASTEXITCODE -eq 0) { throw 'A mismatched executable checksum was accepted.' }
if (@(Get-ChildItem $package -Directory -Filter 'playtest-*').Count -ne 4) { throw 'Checksum failure created a session.' }
# Exercise the exit/report path with a tiny executable, without installed games.
Remove-Item -LiteralPath $binary
Add-Type -OutputAssembly $binary -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.IO;
using System.Threading;
public static class ReachLaunchFixture {
    public static int Main(string[] args) {
        int index = Array.IndexOf(args, "fs_savepath");
        if (index < 0) { return 4; }
        string mod = Path.Combine(args[index + 1], "reach_lab");
        int logIndex = Array.IndexOf(args, "logFileName");
        if (logIndex < 0) { return 5; }
        File.WriteAllText(args[logIndex + 1], "fixture explicit diagnostic log");
        string baseFolder = Path.Combine(args[index + 1], "base");
        Directory.CreateDirectory(baseFolder);
        File.WriteAllText(Path.Combine(baseFolder, "qconsole.log"), "fixture fallback diagnostic log");
        Thread.Sleep(2500);
        return 3;
    }
}
'@
@{ sha256 = (Get-FileHash $binary -Algorithm SHA256).Hash } | ConvertTo-Json | Set-Content (Join-Path $package 'build-sha256.json')
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -Windowed -StockCombat -SingleThreaded -Diagnostics
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic reporting failed for a nonzero fixture exit.' }
$report = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object {
    $path = Join-Path $_.FullName 'exit-report.json'
    if (Test-Path $path) { Get-Content $path -Raw | ConvertFrom-Json }
})
if ($report.Count -ne 1 -or $report[0].exitCode -ne 3 -or $report[0].exitCodeHex -ne '0x00000003') { throw 'Fixture exit code was lost.' }
$zips = @(Get-ChildItem $package -Filter 'reach-diagnostics-*.zip')
if ($zips.Count -ne 1) { throw 'Expected one diagnostic ZIP.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($zips[0].FullName)
try {
    $names = @($archive.Entries | ForEach-Object { $_.FullName })
    foreach ($required in @('qconsole.log', 'qconsole-1.log', 'console-log-index.json', 'process-health.jsonl', 'exit-report.json', 'launch-plan.json')) {
        if ($names -notcontains $required) { throw "Diagnostic ZIP is missing $required." }
    }
    foreach ($name in $names) {
        if ($name -notin @('qconsole.log', 'qconsole-1.log', 'console-log-index.json', 'process-health.jsonl', 'exit-report.json', 'launch-plan.json', 'hardware.json')) {
            throw "Unexpected/private content in diagnostic ZIP: $name"
        }
    }
} finally { $archive.Dispose() }
$global:LASTEXITCODE = 0
Write-Host '::notice title=Playtest launcher::PASS: isolated comparisons, desktop/logging options, backup/checksum protections, nonzero fixture exit and diagnostic ZIP whitelist; no game was launched'
