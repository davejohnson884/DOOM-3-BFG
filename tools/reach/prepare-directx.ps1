[CmdletBinding()]
param([string]$Destination = (Join-Path $env:RUNNER_TEMP 'reach-directx-june2010'))
$ErrorActionPreference = 'Stop'
if (-not $env:RUNNER_TEMP) {
    throw 'Run this SDK preparation on a GitHub Windows runner, or supply RUNNER_TEMP explicitly.'
}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$installer = Join-Path $Destination 'DXSDK_Jun10.exe'
$uri = 'https://download.microsoft.com/download/A/E/7/AE743F1F-632B-4809-87A9-9F2A2791BAA1/DXSDK_Jun10.exe'
Invoke-WebRequest -Uri $uri -OutFile $installer
$signature = Get-AuthenticodeSignature $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation(?:,|$)') {
    throw "DirectX SDK Microsoft signature verification failed: $($signature.Status)"
}
# Extract only; no system SDK installer or registry changes are needed on a runner.
& 7z x $installer "-o$Destination/extracted" -y
if ($LASTEXITCODE -ne 0) { throw 'DirectX SDK extraction failed.' }
$header = Get-ChildItem (Join-Path $Destination 'extracted') -Filter X3DAudio.h -Recurse |
    Where-Object { $_.Directory.Name -ieq 'Include' } | Select-Object -First 1
if (-not $header) { throw 'The SDK archive did not contain Include/X3DAudio.h.' }
$sdk = $header.Directory.Parent.FullName
foreach ($relative in @('Include/dinput.h', 'Include/DxErr.h', 'Lib/x86/DxErr.lib', 'Lib/x86/X3DAudio.lib')) {
    if (-not (Test-Path (Join-Path $sdk $relative))) { throw "Missing SDK dependency: $relative" }
}
if (-not $env:GITHUB_ENV) { throw 'GITHUB_ENV is required to register the SDK for subsequent steps.' }
"DXSDK_DIR=$sdk\" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
