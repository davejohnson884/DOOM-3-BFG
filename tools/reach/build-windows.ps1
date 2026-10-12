[CmdletBinding()]
param([string]$Toolset = '', [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not $env:DXSDK_DIR -or -not (Test-Path (Join-Path $env:DXSDK_DIR 'Include/X3DAudio.h'))) {
    throw 'DXSDK_DIR must point to the June 2010 DirectX SDK.'
}
$msbuild = Get-Command MSBuild.exe -ErrorAction Stop
$buildDirectory = Join-Path $root 'build'
New-Item -ItemType Directory -Force -Path $buildDirectory | Out-Null
$arguments = @(
    (Join-Path $root 'neo/doom3.sln'), '/m:2', '/t:Build',
    "/p:Configuration=$Configuration", '/p:Platform=Win32',
    '/v:minimal', "/flp:logfile=$buildDirectory/reach-build.log;verbosity=normal",
    "/bl:$buildDirectory/reach-build.binlog"
)
if ($Toolset) { $arguments += "/p:PlatformToolset=$Toolset" }
Push-Location (Join-Path $root 'neo')
try {
    & $msbuild.Source @arguments
    if ($LASTEXITCODE -ne 0) {
        $buildExit = $LASTEXITCODE
        if (Test-Path (Join-Path $buildDirectory 'reach-build.log')) {
            $errors = Get-Content (Join-Path $buildDirectory 'reach-build.log') |
                Where-Object { $_ -match '(?:fatal )?error [A-Z]+[0-9]+\s*:' } |
                Select-Object -Unique -First 15
            foreach ($line in $errors) {
                $message = $line.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
                Write-Host "::error title=Windows compiler::$message"
            }
            $warnings = Get-Content (Join-Path $buildDirectory 'reach-build.log') |
                Where-Object { $_ -match 'warning [A-Z]+[0-9]+\s*:' } |
                Select-Object -Unique -First 8
            foreach ($line in $warnings) {
                $message = $line.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
                Write-Host "::warning title=Windows compiler::$message"
            }
        }
        throw "MSBuild failed with exit code $buildExit. See build/reach-build.log."
    }
    $binary = Join-Path $buildDirectory "Win32/$Configuration/doomexe.exe"
    if (-not (Test-Path $binary)) { throw "MSBuild returned success but the executable was missing: $binary" }
    Write-Host "Built $binary"
} finally {
    Pop-Location
}
