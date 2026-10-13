[CmdletBinding()]
param([string]$AssetDirectory = '')
$ErrorActionPreference = 'Stop'
trap {
    Write-Host "Script fix failed: $($_.Exception.Message)"
    exit 1
}
if ([string]::IsNullOrWhiteSpace($AssetDirectory)) {
    $pointer = Join-Path $PSScriptRoot 'reach-weapon-data.path'
    if (-not (Test-Path -LiteralPath $pointer -PathType Leaf)) {
        throw 'Extract these fix files into the same folder as Start-Reach-rifle-stock.cmd and reach-weapon-data.path.'
    }
    $AssetDirectory = (Get-Content -LiteralPath $pointer -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($AssetDirectory)) { throw 'The converted asset folder path is empty.' }
$assets = (Resolve-Path -LiteralPath $AssetDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $assets 'weapon-tuning.json') -PathType Leaf)) {
    throw 'This is not a generated Reach rifle pack.'
}
$script = Join-Path $assets 'stock-script/weapon_machinegun.script'
$text = [IO.File]::ReadAllText($script)
if (-not $text.StartsWith('// Original project code.') -or $text -notmatch 'float weapon_machinegun::RetailReachPose\(\)') {
    throw 'The script is not this project''s retail preview; no changes made.'
}
$oldNames = [regex]::Matches($text, '\bmove\b').Count
if ($oldNames -eq 0 -and $text -match 'vector reach_move_vector;') {
    Write-Host 'The rifle script is already fixed. Start-Reach-rifle-stock.cmd is ready.'
    exit 0
}
if ($oldNames -ne 3 -or $text -notmatch 'vector move;' -or $text -notmatch 'move = owner.getMove\(\);' -or $text -notmatch 'sys.vecLength\(move\)') {
    throw 'The script differs from the affected version; no changes made.'
}
$backup = $script + '.before-move-fix-' + [Guid]::NewGuid().ToString('N') + '.bak'
Copy-Item -LiteralPath $script -Destination $backup
$fixed = [regex]::Replace($text, '\bmove\b', 'reach_move_vector')
[IO.File]::WriteAllText($script, $fixed, (New-Object Text.UTF8Encoding($false)))
Write-Host 'Fixed the rifle script. Your converted models, animations and sounds are ready to reuse.'
Write-Host 'Close BFG, then double-click Start-Reach-rifle-stock.cmd again.'
