[CmdletBinding()]
param([string]$Toolset = '', [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release')
$ErrorActionPreference = 'Stop'
trap {
    $message = $_.ToString().Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Host "::error title=Windows build::$message"
    exit 1
}
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
if ($Toolset) {
    $arguments += "/p:PlatformToolset=$Toolset"
    $arguments += "/p:ForceImportBeforeCppTargets=$(Join-Path $PSScriptRoot 'modern-msvc.props')"
}
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
    $binary = Join-Path $buildDirectory "Win32/$Configuration/Doom3BFG.exe"
    if (-not (Test-Path $binary)) { throw "MSBuild returned success but the executable was missing: $binary" }
    $package = Join-Path $buildDirectory 'reach-playtest'
    if ((Test-Path $package) -and -not (Test-Path (Join-Path $package '.reach-generated'))) {
        throw 'The package output directory already exists without a generation marker; move it aside before building.'
    }
    New-Item -ItemType Directory -Path $package -Force | Out-Null
    Set-Content (Join-Path $package '.reach-generated') 'Generated Reach playtest package'
    Copy-Item $binary (Join-Path $package 'Doom3BFG.exe') -Force
    foreach ($file in @('start-playtest.ps1', 'Start-Reach-playtest.cmd', 'reach_prototype.cfg', 'PLAYTEST.md')) {
        Copy-Item (Join-Path $PSScriptRoot $file) (Join-Path $package $file) -Force
    }
    @{ sha256 = (Get-FileHash $binary -Algorithm SHA256).Hash } | ConvertTo-Json |
        Set-Content (Join-Path $package 'build-sha256.json') -Encoding UTF8
    Write-Host "Built $binary"
} finally {
    Pop-Location
}
