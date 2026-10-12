[CmdletBinding()]
param(
    [string]$BfgPath = 'C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition',
    [string]$MccPath = 'D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection',
    [string]$OutputDirectory = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
$report = [ordered]@{ collectedUtc = [DateTime]::UtcNow.ToString('o'); games = @() }
foreach ($game in @(
    @{ name = 'Doom 3 BFG'; path = $BfgPath; scan = 'base'; extensions = @('.resources', '.cfg', '.exe') },
    @{ name = 'MCC Reach'; path = $MccPath; scan = 'haloreach'; extensions = @('.map', '.fsb', '.info', '.dll') }
)) {
    if (-not (Test-Path -LiteralPath $game.path -PathType Container)) {
        throw "Install folder not found: $($game.path)"
    }
    $root = (Resolve-Path -LiteralPath $game.path).Path.TrimEnd('\')
    $scan = Join-Path $root $game.scan
    if (-not (Test-Path -LiteralPath $scan -PathType Container)) {
        throw "Required game data folder not found: $scan. Check that Reach is installed in MCC."
    }
    $files = @(Get-ChildItem -LiteralPath $scan -File -Recurse |
        Where-Object { $_.Extension.ToLowerInvariant() -in $game.extensions } |
        Sort-Object FullName | ForEach-Object {
            [ordered]@{ path = $_.FullName.Substring($root.Length + 1); bytes = $_.Length }
        })
    $executables = @(Get-ChildItem -LiteralPath $root -Filter '*.exe' -File | ForEach-Object {
        [ordered]@{ name = $_.Name; version = $_.VersionInfo.FileVersion }
    })
    $report.games += [ordered]@{ name = $game.name; install = $root; executables = $executables; files = $files }
}
if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    throw 'Choose an existing output directory outside the Steam game folders.'
}
$outputRoot = (Resolve-Path -LiteralPath $OutputDirectory).Path.TrimEnd('\')
foreach ($game in $report.games) {
    if ($outputRoot -ieq $game.install -or $outputRoot.StartsWith($game.install + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The report must be saved outside both game installations.'
    }
}
$output = Join-Path $outputRoot ('reach-install-info-' + [Guid]::NewGuid().ToString('N') + '.json')
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $output -Encoding UTF8
Write-Host "Created $output"
Write-Host 'This contains file names, sizes, install paths and executable versions only. No game data was copied or changed.'
