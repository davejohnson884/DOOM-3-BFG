[CmdletBinding()]
param(
    [string]$BfgPath = 'C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition',
    [string]$OutputDirectory = ''
)
$ErrorActionPreference = 'Stop'
trap {
    Write-Host "Collection error at line $($_.InvocationInfo.ScriptLineNumber): $($_.Exception.Message)"
    Write-Host $_.InvocationInfo.PositionMessage
    exit 1
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { $OutputDirectory = $PSScriptRoot }
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { $OutputDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path }
$install = (Resolve-Path -LiteralPath $BfgPath).Path.TrimEnd('\')
$outputRoot = (Resolve-Path -LiteralPath $OutputDirectory).Path.TrimEnd('\')
if ($outputRoot -ieq $install -or $outputRoot.StartsWith($install + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose an output directory outside the BFG installation.'
}
$bundle = Join-Path $outputRoot ('reach-combat-data-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $bundle | Out-Null
$manifest = @()
$total = 0L

function Read-UInt32BE([System.IO.BinaryReader]$Reader) {
    [byte[]]$bytes = $Reader.ReadBytes(4)
    if ($bytes.Length -ne 4) { throw 'Truncated resource integer.' }
    [Array]::Reverse($bytes)
    return [BitConverter]::ToUInt32($bytes, 0)
}

# Format follows neo/framework/File_Resource.cpp and File.cpp: big-endian
# header/count/offsets, little-endian string length, raw file payloads.
foreach ($container in @('_common.resources', '_ordered.resources')) {
    $resource = Join-Path $install ('base/' + $container)
    $stream = [System.IO.File]::Open($resource, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    $reader = New-Object System.IO.BinaryReader($stream)
    try {
        if ((Read-UInt32BE $reader) -ne [uint32]3489660941) { throw "Unexpected resource format: $container" }
        [long]$tableOffset = Read-UInt32BE $reader
        [long]$tableLength = Read-UInt32BE $reader
        [long]$tableEnd = $tableOffset + $tableLength
        if ($tableOffset -lt 12 -or $tableLength -lt 4 -or $tableLength -gt 64MB -or $tableEnd -gt $stream.Length) {
            throw "Invalid resource table bounds: $container"
        }
        $stream.Position = $tableOffset
        $count = Read-UInt32BE $reader
        if ($count -gt 1000000) { throw 'Resource entry count exceeds the supported limit.' }
        for ($i = 0; $i -lt $count; $i++) {
            if ($stream.Position + 4 -gt $tableEnd) { throw 'Truncated resource name length.' }
            $nameLength = $reader.ReadInt32()
            if ($nameLength -le 0 -or $nameLength -gt 4096 -or $stream.Position + $nameLength + 8 -gt $tableEnd) {
                throw 'Invalid resource filename length.'
            }
            $name = [Text.Encoding]::UTF8.GetString($reader.ReadBytes($nameLength)).Replace('\', '/')
            [long]$offset = Read-UInt32BE $reader
            [long]$length = Read-UInt32BE $reader
            if ($offset -lt 12 -or $offset + $length -gt $stream.Length) { throw "Invalid payload bounds: $name" }
            if ([IO.Path]::GetExtension($name).ToLowerInvariant() -notin @('.def', '.script')) { continue }
            if ($name -match '(^/|:|(^|/)\.\.?(/|$))' -or $name.IndexOf([char]0) -ge 0) { throw "Unsafe resource path: $name" }
            $total += $length
            if ($length -gt 16MB -or $total -gt 25MB) { throw 'Text collection exceeds the size limit; no ZIP will be produced.' }
            $relative = [IO.Path]::GetFileNameWithoutExtension($container) + '/' + $i + '/' + $name
            $target = [IO.Path]::GetFullPath((Join-Path $bundle $relative))
            if (-not $target.StartsWith($bundle + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Resource path escaped the output folder.' }
            $resume = $stream.Position
            $stream.Position = $offset
            [byte[]]$payload = $reader.ReadBytes([int]$length)
            if ($payload.Length -ne $length) { throw "Truncated text payload: $name" }
            $stream.Position = $resume
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            [IO.File]::WriteAllBytes($target, $payload)
            $manifest += [ordered]@{ container = $container; name = $name; bytes = $length; output = $relative }
        }
    } finally { $reader.Dispose() }
}
if ($manifest.Count -eq 0) { throw 'No .def or .script files were found; no ZIP will be produced.' }
$manifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $bundle 'manifest.json') -Encoding UTF8
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = $bundle + '.zip'
[IO.Compression.ZipFile]::CreateFromDirectory($bundle, $zip)
Write-Host "Collected $($manifest.Count) text files into $zip"
Write-Host 'Keep this private; attach the ZIP to the project chat, not GitHub. No models, textures, sounds, saves or game files were changed.'
