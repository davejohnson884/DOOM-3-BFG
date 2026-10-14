param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Dependencies
)
$ErrorActionPreference = 'Stop'
$Source = (Resolve-Path -LiteralPath $Source).Path
New-Item -ItemType Directory -Path $Dependencies -Force | Out-Null
$Dependencies = (Resolve-Path -LiteralPath $Dependencies).Path
$pins = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-dependencies.json') -Raw | ConvertFrom-Json

function Get-VerifiedDependency($pin, [string]$destination) {
    if (-not (Test-Path -LiteralPath $destination)) {
        Invoke-WebRequest -Uri $pin.url -OutFile $destination
    }
    $actual = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $pin.sha256) { throw "Dependency checksum mismatch: $destination" }
    Write-Host "Verified $(Split-Path -Leaf $destination): $actual"
}

$dxcArchive = Join-Path $Dependencies 'dxc.zip'
$ispcArchive = Join-Path $Dependencies 'ispc.zip'
$exports = Join-Path $Dependencies 'vulkan-1.def'
Get-VerifiedDependency $pins.dxc $dxcArchive
Get-VerifiedDependency $pins.ispc $ispcArchive
Get-VerifiedDependency $pins.vulkan_exports $exports
Expand-Archive -LiteralPath $dxcArchive -DestinationPath (Join-Path $Dependencies 'dxc') -Force
Expand-Archive -LiteralPath $ispcArchive -DestinationPath (Join-Path $Dependencies 'ispc') -Force

$dxc = Join-Path $Dependencies 'dxc/bin/x64/dxc.exe'
$ispc = Join-Path $Dependencies 'ispc/ispc-v1.23.0-windows/bin/ispc.exe'
$vulkanHeaders = Join-Path $Source 'neo/extern/nvrhi/thirdparty/Vulkan-Headers/include'
$vulkanLibrary = Join-Path $Dependencies 'vulkan-1.lib'
if (-not (Test-Path -LiteralPath (Join-Path $vulkanHeaders 'vulkan/vulkan_core.h'))) {
    throw 'Initialize the exact upstream submodules before configuring the build.'
}
# Standard Windows import library from pinned Khronos exports, used only to build.
# No Vulkan DLL or SDK changes are installed on the player's PC.
& lib.exe "/def:$exports" /machine:x64 "/out:$vulkanLibrary"
if ($LASTEXITCODE -ne 0) { throw "Vulkan import-library creation failed: $LASTEXITCODE" }

$shaderTools = Join-Path $Source 'neo/bin/Release'
New-Item -ItemType Directory -Path $shaderTools -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Dependencies 'dxc/bin/x64/dxcompiler.dll'), (Join-Path $Dependencies 'dxc/bin/x64/dxil.dll') -Destination $shaderTools -Force

& cmake -S (Join-Path $Source 'neo') -B (Join-Path $Source 'build-reach') -G 'Visual Studio 17 2022' -A x64 `
    -DFFMPEG=OFF -DBINKDEC=ON -DOPENAL=OFF -DUSE_DX12=ON -DUSE_VULKAN=ON `
    "-DISPC_EXECUTABLE=$ispc" "-DVulkan_INCLUDE_DIR=$vulkanHeaders" "-DVulkan_LIBRARY=$vulkanLibrary" `
    "-DDXC_PATH=$dxc" "-DDXC_SPIRV_PATH=$dxc" "-DDXC_DXIL_EXECUTABLE=$dxc" "-DDXC_SPIRV_EXECUTABLE=$dxc"
if ($LASTEXITCODE -ne 0) { throw "RBDoom CMake configuration failed: $LASTEXITCODE" }
