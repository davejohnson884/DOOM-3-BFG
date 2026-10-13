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
# Model a Steam install that also contains another port's incompatible cache.
foreach ($directory in @('base/renderprogs/glsl', 'base/newfonts', 'reach_lab/renderprogs/glsl', 'base/maps', 'base/video', 'base/wads')) {
    New-Item -ItemType Directory -Path (Join-Path $bfg $directory) -Force | Out-Null
}
Set-Content (Join-Path $bfg 'base/renderprogs/glsl/gui_vertex.glsl') 'incompatible loose shader'
Set-Content (Join-Path $bfg 'base/newfonts/fixture.dat') 'incompatible loose font'
Set-Content (Join-Path $bfg 'reach_lab/renderprogs/glsl/gui_vertex.glsl') 'old source port shader cache'
Set-Content (Join-Path $bfg 'base/maps/mars_city1.resources') 'stock map fixture'
Set-Content (Join-Path $bfg 'base/video/mars_rotation.bik') 'stock video fixture'
Set-Content (Join-Path $bfg 'base/wads/doom.wad') 'stock classic fixture'
Set-Content (Join-Path $bfg 'base/default.cfg') 'stock input defaults'
$originalResourceHash = (Get-FileHash (Join-Path $bfg 'base/_common.resources') -Algorithm SHA256).Hash
$originalProfile = Join-Path $saved 'id Software/DOOM 3 BFG/base'
New-Item -ItemType Directory -Path $originalProfile -Force | Out-Null
$stockConfig = Join-Path $originalProfile 'D3BFGConfig.cfg'
Set-Content $stockConfig 'seta r_fullscreen "2"'
$stockConfigHash = (Get-FileHash $stockConfig -Algorithm SHA256).Hash
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -ReachRifle -RetailRifle -Windowed -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Retail rifle staging failed.' }
$retailPlans = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object { Get-Content (Join-Path $_.FullName 'launch-plan.json') -Raw | ConvertFrom-Json })
$retailPlan = @($retailPlans | Where-Object { $_.binary -eq (Join-Path $bfg 'Doom3BFG.exe') })[0]
if ($null -eq $retailPlan -or $retailPlan.arguments -notmatch '\+set logFile 0\b') { throw 'Retail preview did not use the installed executable with normal logging disabled.' }
if ((Get-Content (Join-Path $retailPlan.profile 'reach_lab/script/weapon_machinegun.script') -Raw).Trim() -ne 'retail script fixture') { throw 'Retail preview used a script requiring new native events.' }
if ($retailPlan.data -eq $bfg -or -not $retailPlan.data.StartsWith($package) -or $retailPlan.arguments -notmatch [regex]::Escape('+set fs_basepath "' + $retailPlan.data + '"')) { throw 'Retail preview still searches the mixed installation data tree.' }
foreach ($relative in @('base/_common.resources', 'base/_ordered.resources', 'base/maps/mars_city1.resources', 'base/video/mars_rotation.bik', 'base/wads/doom.wad', 'base/default.cfg')) {
    $linked = Join-Path $retailPlan.data $relative
    if (-not (Test-Path -LiteralPath $linked) -or (Get-Item -LiteralPath $linked).LinkType -ne 'HardLink') { throw "Stock data was not linked without duplication: $relative" }
    if ((Get-FileHash $linked -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $bfg $relative) -Algorithm SHA256).Hash) { throw "Stock data contents changed: $relative" }
}
foreach ($relative in @('base/renderprogs', 'base/newfonts', 'reach_lab')) {
    if (Test-Path -LiteralPath (Join-Path $retailPlan.data $relative)) { throw "Incompatible loose renderer data leaked into the retail view: $relative" }
}
if (-not $retailPlan.copiedStockConfig -or (Get-FileHash (Join-Path $retailPlan.profile 'reach_lab/D3BFGConfig.cfg') -Algorithm SHA256).Hash -ne $stockConfigHash -or (Get-FileHash $stockConfig -Algorithm SHA256).Hash -ne $stockConfigHash) { throw 'Active mod config differs from the unchanged stock config.' }
if ($retailPlan.arguments -notmatch '\+set r_windowX -?\d+\b' -or $retailPlan.arguments -notmatch '\+set r_windowY -?\d+\b') { throw 'Explicit windowed launch does not choose a desktop position.' }
# The normal retail launcher must retain the working stock monitor/settings.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -ReachRifle -RetailRifle -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Normal retail preparation failed.' }
$normalPlans = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object { Get-Content (Join-Path $_.FullName 'launch-plan.json') -Raw | ConvertFrom-Json })
$normal = @($normalPlans | Where-Object { $_.binary -eq (Join-Path $bfg 'Doom3BFG.exe') -and $_.arguments -notmatch '\+set r_fullscreen' })
if ($normal.Count -ne 1 -or -not $normal[0].copiedStockConfig) { throw 'Normal retail launch overrides the working stock display config.' }
# Without a stock config, use the primary desktop instead of default monitor 1.
Remove-Item -LiteralPath $stockConfig
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $package 'start-playtest.ps1') -BfgPath $bfg -SavedGamesDirectory $saved -ReachRifle -RetailRifle -PrepareOnly
if ($LASTEXITCODE -ne 0) { throw 'Retail missing-config fallback preparation failed.' }
$fallbackPlans = @(Get-ChildItem $package -Directory -Filter 'playtest-*' | ForEach-Object { Get-Content (Join-Path $_.FullName 'launch-plan.json') -Raw | ConvertFrom-Json })
$fallback = @($fallbackPlans | Where-Object { $_.binary -eq (Join-Path $bfg 'Doom3BFG.exe') -and -not $_.copiedStockConfig })
if ($fallback.Count -ne 1 -or $fallback[0].arguments -notmatch '\+set r_fullscreen -1\b') { throw 'Missing stock config fell back to the wrong monitor.' }
if ((Get-FileHash (Join-Path $bfg 'base/_common.resources') -Algorithm SHA256).Hash -ne $originalResourceHash -or (Get-Content (Join-Path $bfg 'reach_lab/renderprogs/glsl/gui_vertex.glsl') -Raw).Trim() -ne 'old source port shader cache') { throw 'Original stock archive or old port cache changed.' }
foreach ($retail in @($retailPlan, $normal[0], $fallback[0])) {
    if ($retail.arguments -match '\+set (com_smp|jobs_numThreads|r_useParallel\w+|r_useUniformArrays)\b') { throw 'Retail launcher changed rendering/thread settings.' }
}
Write-Host '::notice title=Rifle staging::PASS: packaged-data hardlinks, incompatible shader/font/cache exclusion, active stock display config and primary-desktop fallback; neither game launched'
