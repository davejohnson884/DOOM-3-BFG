$ErrorActionPreference = 'Stop'
$testRoot = Join-Path $env:RUNNER_TEMP ('reach-inventory-test-' + [Guid]::NewGuid().ToString('N'))
$bfg = Join-Path $testRoot 'Steam BFG'
$mcc = Join-Path $testRoot 'Steam MCC'
$out = Join-Path $testRoot 'Output'
foreach ($directory in @((Join-Path $bfg 'base'), (Join-Path $mcc 'haloreach/maps'), $out)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
Set-Content (Join-Path $bfg 'base/test.resources') 'resource inventory fixture'
Set-Content (Join-Path $mcc 'haloreach/maps/test.map') 'map inventory fixture'
Copy-Item (Join-Path $PSScriptRoot 'collect-install-info.ps1') $out
$script = Join-Path $out 'collect-install-info.ps1'
# Exercise Windows PowerShell 5.1's -File invocation and both output-path modes.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -BfgPath $bfg -MccPath $mcc
if ($LASTEXITCODE -ne 0) { throw 'Inventory failed with its default output path.' }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -BfgPath $bfg -MccPath $mcc -OutputDirectory ($out + '\.')
if ($LASTEXITCODE -ne 0) { throw 'Inventory failed with the launcher-style output path.' }
$reports = @(Get-ChildItem $out -Filter 'reach-install-info-*.json')
if ($reports.Count -ne 2) { throw 'Inventory did not create two distinct reports.' }
foreach ($report in $reports) {
    $data = Get-Content $report.FullName -Raw | ConvertFrom-Json
    if ($data.games.Count -ne 2 -or $data.games[0].files.Count -ne 1 -or $data.games[1].files.Count -ne 1) {
        throw 'Inventory did not report the expected game data.'
    }
}
Write-Host 'PASS: Windows PowerShell default/explicit output paths and inventory report contents'
