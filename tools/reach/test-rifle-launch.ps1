$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('reach-rifle-stage-' + [Guid]::NewGuid().ToString('N'))
$package = Join-Path $root 'Package'
$bfg = Join-Path $root 'Steam BFG'
$assets = Join-Path $root 'Converted Assets'
$saved = Join-Path $root 'Saved Games'
New-Item -ItemType Directory -Path $package, (Join-Path $bfg 'base'), $assets, $saved -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'start-playtest.ps1'), (Join-Path $PSScriptRoot 'reach_prototype.cfg') $package
Set-Content (Join-Path $bfg 'base/_common.resources') 'unchanged source fixture'
Set-Content (Join-Path $bfg 'base/_ordered.resources') 'unchanged source fixture'
$binary = Join-Path $package 'Doom3BFG.exe'
Set-Content $binary 'fixture; must never launch'
@{ sha256 = (Get-FileHash $binary -Algorithm SHA256).Hash } | ConvertTo-Json | Set-Content (Join-Path $package 'build-sha256.json')
foreach ($directory in @('models', 'materials', 'textures', 'sound', 'def', 'script')) {
    New-Item -ItemType Directory -Path (Join-Path $assets $directory) | Out-Null
    Set-Content (Join-Path $assets ($directory + '/fixture.txt')) $directory
}
Set-Content (Join-Path $assets 'def/weapon_machinegun.def') 'fixture declaration'
Set-Content (Join-Path $assets 'script/weapon_machinegun.script') 'fixture script'
Set-Content (Join-Path $assets 'weapon-tuning.json') '{}'
New-Item -ItemType Directory -Path (Join-Path $assets 'stock-script') | Out-Null
Set-Content (Join-Path $assets 'stock-script/weapon_machinegun.script') 'retail script fixture'
@{ clips = 25; framesChecked = 844 } | ConvertTo-Json | Set-Content (Join-Path $assets 'validation-report.json')
Set-Content (Join-Path $package 'reach-weapon-data.path') $assets
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -ReachRifle -Windowed -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Rifle lab staging failed.' }
$session = @(Get-ChildItem $package -Directory -Filter 'playtest-*')[0]
$plan = Get-Content (Join-Path $session.FullName 'launch-plan.json') -Raw | ConvertFrom-Json
if ($plan.threading -ne 'normal-threading' -or $plan.arguments -match '\+set (com_smp|jobs_numThreads)') { throw 'Rifle launcher changed stock threading.' }
if ($plan.arguments -notmatch '\+set fs_resourceLoadPriority 0\b') { throw 'Loose converted assets would not override stock resources.' }
foreach ($directory in @('models', 'materials', 'textures', 'sound', 'def', 'script')) {
    if (-not (Test-Path (Join-Path $plan.profile ('reach_lab/' + $directory + '/fixture.txt')))) { throw "Rifle asset category not copied: $directory" }
}
if ((Get-Content (Join-Path $bfg 'base/_common.resources') -Raw).Trim() -ne 'unchanged source fixture') { throw 'Original game data changed.' }
Set-Content (Join-Path $bfg 'Doom3BFG.exe') 'retail fixture; must never launch'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -ReachRifle -RetailRifle -Windowed -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Retail rifle staging failed.' }
$retailPlans = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object { Get-Content (Join-Path $_.FullName 'launch-plan.json') -Raw | ConvertFrom-Json })
$retailPlan = @($retailPlans | Where-Object { $_.binary -eq (Join-Path $bfg 'Doom3BFG.exe') })[0]
if ($null -eq $retailPlan -or $retailPlan.arguments -notmatch '\+set logFile 0\b') { throw 'Retail preview did not use the installed executable with normal logging disabled.' }
if ((Get-Content (Join-Path $retailPlan.profile 'reach_lab/script/weapon_machinegun.script') -Raw).Trim() -ne 'retail script fixture') { throw 'Retail preview used a script requiring new native events.' }
Write-Host '::notice title=Rifle staging::PASS: converted assets staged in an isolated profile with resource override and stock threading; neither game launched'
