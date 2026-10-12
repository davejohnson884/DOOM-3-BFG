$ErrorActionPreference = 'Stop'
$testRoot = Join-Path $env:RUNNER_TEMP ('reach-resource-test-' + [Guid]::NewGuid().ToString('N'))
$bfg = Join-Path $testRoot 'Steam BFG'
$output = Join-Path $testRoot 'Output'
New-Item -ItemType Directory -Path (Join-Path $bfg 'base'), $output -Force | Out-Null

function Write-UInt32BE([IO.BinaryWriter]$Writer, [uint32]$Value) {
    [byte[]]$bytes = [BitConverter]::GetBytes($Value)
    [Array]::Reverse($bytes)
    $Writer.Write($bytes)
}
function Make-Resource([string]$Path, [string]$ScriptName = 'script/test.script') {
    $stream = [IO.File]::Create($Path)
    $writer = New-Object IO.BinaryWriter($stream)
    try {
        [byte[]]$script = [Text.Encoding]::UTF8.GetBytes('void test() {}')
        [byte[]]$model = [Text.Encoding]::UTF8.GetBytes('model must not be collected')
        $tableOffset = 12 + $script.Length + $model.Length
        $names = @($ScriptName, 'models/test.md5mesh')
        $tableLength = 4
        foreach ($name in $names) { $tableLength += 12 + [Text.Encoding]::UTF8.GetByteCount($name) }
        Write-UInt32BE $writer 3489660941
        Write-UInt32BE $writer $tableOffset
        Write-UInt32BE $writer $tableLength
        $writer.Write($script)
        $writer.Write($model)
        Write-UInt32BE $writer 2
        for ($i = 0; $i -lt 2; $i++) {
            [byte[]]$name = [Text.Encoding]::UTF8.GetBytes($names[$i])
            $writer.Write([int]$name.Length)
            $writer.Write($name)
            if ($i -eq 0) {
                Write-UInt32BE $writer 12
                Write-UInt32BE $writer $script.Length
            } else {
                Write-UInt32BE $writer (12 + $script.Length)
                Write-UInt32BE $writer $model.Length
            }
        }
    } finally { $writer.Dispose() }
}
Make-Resource (Join-Path $bfg 'base/_common.resources')
Make-Resource (Join-Path $bfg 'base/_ordered.resources')
$collector = Join-Path $PSScriptRoot 'collect-combat-data.ps1'
$result = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -BfgPath $bfg -OutputDirectory $output
if ($LASTEXITCODE -ne 0) { throw ('Resource text collection failed: ' + ($result -join ' ')) }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = @(Get-ChildItem $output -Filter '*.zip')
if ($zip.Count -ne 1) { throw 'Expected one resource ZIP.' }
$archive = [IO.Compression.ZipFile]::OpenRead($zip[0].FullName)
try {
    $entries = @($archive.Entries)
    $scripts = @($entries | Where-Object { $_.FullName.EndsWith('.script') })
    if ($scripts.Count -ne 2 -or @($entries | Where-Object { $_.FullName.EndsWith('.md5mesh') }).Count -ne 0) {
        throw 'Text filtering or container provenance failed.'
    }
    foreach ($entry in $scripts) {
        $textReader = New-Object IO.StreamReader($entry.Open())
        try { if ($textReader.ReadToEnd() -ne 'void test() {}') { throw 'Payload bytes changed.' } }
        finally { $textReader.Dispose() }
    }
} finally { $archive.Dispose() }
Make-Resource (Join-Path $bfg 'base/_common.resources') '../escape.script'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -BfgPath $bfg -OutputDirectory $output
if ($LASTEXITCODE -eq 0) { throw 'An unsafe archive path was accepted.' }
if (@(Get-ChildItem $output -Filter '*.zip').Count -ne 1) { throw 'Invalid input produced a ZIP.' }
Write-Host 'PASS: resource endianness, text-only extraction, exact payloads and traversal rejection'
# The deliberately rejected archive exited 1, and all assertions above checked
# that outcome. GitHub's PowerShell wrapper otherwise returns that stale native
# exit code even when the test script completes successfully.
$global:LASTEXITCODE = 0
Write-Host '::notice title=Resource collector test::PASS: valid text extraction and expected rejection of an unsafe archive'
