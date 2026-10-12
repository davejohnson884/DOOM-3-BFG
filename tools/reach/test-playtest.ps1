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
$mod = Join-Path $plan.profile 'reach_lab'
if (-not (Test-Path (Join-Path $mod 'reach_prototype.cfg')) -or
    (Get-Content (Join-Path $mod 'autoexec.cfg') -Raw).Trim() -ne 'exec reach_prototype.cfg' -or
    $plan.arguments -notmatch '\+set g_reachLabAutoConfig 1') {
    throw 'The lab configuration was not staged for startup and post-spawn loading.'
}
$backupFile = Join-Path $session[0].FullName 'backup-original-profile/existing-save.txt'
if ((Get-Content $backupFile -Raw).Trim() -ne 'preserve this profile' -or
    (Get-Content (Join-Path $original 'existing-save.txt') -Raw).Trim() -ne 'preserve this profile') {
    throw 'The original profile was not preserved and backed up.'
}
Set-Content $binary 'modified fixture'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -PrepareOnly
if ($LASTEXITCODE -eq 0) { throw 'A mismatched executable checksum was accepted.' }
if (@(Get-ChildItem $package -Directory -Filter 'playtest-*').Count -ne 1) { throw 'Checksum failure created a session.' }
$global:LASTEXITCODE = 0
Write-Host '::notice title=Playtest launcher::PASS: isolated profile, original-save backup and checksum rejection; no game was launched'
