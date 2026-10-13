$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('reach-script-fix-' + [Guid]::NewGuid().ToString('N'))
$package = Join-Path $root 'Package'
$assets = Join-Path $root 'Converted Assets'
New-Item -ItemType Directory -Path $package, (Join-Path $assets 'stock-script') -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'fix-rifle-script.ps1') $package
Set-Content (Join-Path $package 'reach-weapon-data.path') $assets
Set-Content (Join-Path $assets 'weapon-tuning.json') '{}'
$script = Join-Path $assets 'stock-script/weapon_machinegun.script'
$old = @'
// Original project code. Loaded in the machinegun slot of the isolated Reach lab.
float weapon_machinegun::RetailReachPose() {
    entity owner;
    vector move;
    move = owner.getMove();
    return sys.vecLength(move);
}
'@
Set-Content $script $old
$originalText = [IO.File]::ReadAllText($script)
$originalHash = (Get-FileHash $script -Algorithm SHA256).Hash
$helper = Join-Path $package 'fix-rifle-script.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper
if ($LASTEXITCODE -ne 0) { throw 'Script repair failed.' }
$fixed = [IO.File]::ReadAllText($script)
if ($fixed -cne [regex]::Replace($originalText, '\bmove\b', 'reach_move_vector')) { throw 'Unexpected script edit.' }
if ([regex]::Matches($fixed, '\breach_move_vector\b').Count -ne 3 -or $fixed -match '\bmove\b' -or $fixed -notmatch 'owner.getMove\(\)') { throw 'Local rename damaged event calls.' }
$backups = @(Get-ChildItem (Split-Path $script) -Filter '*.bak')
if ($backups.Count -ne 1 -or (Get-FileHash $backups[0].FullName -Algorithm SHA256).Hash -ne $originalHash) { throw 'Original script backup missing or changed.' }
$fixedHash = (Get-FileHash $script -Algorithm SHA256).Hash
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper
if ($LASTEXITCODE -ne 0 -or (Get-FileHash $script -Algorithm SHA256).Hash -ne $fixedHash -or @(Get-ChildItem (Split-Path $script) -Filter '*.bak').Count -ne 1) { throw 'Second repair changed the fixed script.' }
Set-Content $script '// unrelated script'
$unrelatedHash = (Get-FileHash $script -Algorithm SHA256).Hash
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper
if ($LASTEXITCODE -eq 0 -or (Get-FileHash $script -Algorithm SHA256).Hash -ne $unrelatedHash) { throw 'Repair accepted or modified an unrelated script.' }
Write-Host '::notice title=Rifle script repair::PASS: automatic folder lookup, exact local rename, original backup, repeated run and unrelated-script rejection'
