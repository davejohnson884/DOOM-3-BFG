[CmdletBinding()]
param([string]$Destination = (Join-Path $env:RUNNER_TEMP 'reach-directx-june2010'))
$ErrorActionPreference = 'Stop'
trap {
    # Expose the actual setup failure in the public Actions annotations, where
    # it can be diagnosed even when authenticated log access is unavailable.
    $message = $_.ToString().Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Host "::error title=DirectX SDK setup::$message"
    exit 1
}
if (-not $env:RUNNER_TEMP) {
    throw 'Run this SDK preparation on a GitHub Windows runner, or supply RUNNER_TEMP explicitly.'
}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$installer = Join-Path $Destination 'DXSDK_Jun10.exe'
$page = Invoke-WebRequest -Uri 'https://www.microsoft.com/en-us/download/details.aspx?id=6812'
$links = [regex]::Matches($page.Content, 'https://download\.microsoft\.com/download/[^"<>\s\\]+/DXSDK_Jun10\.exe') |
    ForEach-Object { $_.Value } | Select-Object -Unique
if (@($links).Count -ne 1) { throw 'Could not resolve a unique June 2010 SDK download from the Microsoft download page.' }
$uri = @($links)[0]
Write-Host "Downloading SDK from its Microsoft download-page link: $uri"
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
