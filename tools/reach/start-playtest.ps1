[CmdletBinding()]
param(
    [string]$BfgPath = 'C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition',
    [string]$SavedGamesDirectory = '',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
trap {
    Write-Host "Playtest setup error at line $($_.InvocationInfo.ScriptLineNumber): $($_.Exception.Message)"
    exit 1
}
$package = $PSScriptRoot
$binary = Join-Path $package 'Doom3BFG.exe'
$hashFile = Join-Path $package 'build-sha256.json'
if (-not (Test-Path -LiteralPath $binary) -or -not (Test-Path -LiteralPath $hashFile)) {
    throw 'Extract the complete reach-bfg-win32 artifact before running this launcher.'
}
$expected = Get-Content -LiteralPath $hashFile -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash -ine $expected.sha256) {
    throw 'The executable does not match this build package. Download and extract the artifact again.'
}
$install = (Resolve-Path -LiteralPath $BfgPath).Path.TrimEnd('\')
if ($package -ieq $install -or $package.StartsWith($install + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Extract the playtest package outside your Steam game installation.'
}
foreach ($name in @('_common.resources', '_ordered.resources')) {
    if (-not (Test-Path -LiteralPath (Join-Path $install ('base/' + $name)))) { throw "Missing BFG data: $name" }
}
if (-not $PrepareOnly -and @(Get-Process -Name Doom3BFG, RBDoom3BFG, BFAhidef, RBhidef -ErrorAction SilentlyContinue).Count) {
    throw 'Close your existing BFG/source-port game before starting the playtest.'
}
if ([string]::IsNullOrWhiteSpace($SavedGamesDirectory)) {
    Add-Type @'
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class ReachSavedGames {
    [DllImport("shell32.dll")]
    private static extern int SHGetKnownFolderPath([MarshalAs(UnmanagedType.LPStruct)] Guid id, uint flags, IntPtr token, out IntPtr path);
    public static string Resolve() {
        IntPtr path;
        int result = SHGetKnownFolderPath(new Guid("4c5c32ff-bb9d-43b0-b5b4-2d72e54eaaA4"), 0, IntPtr.Zero, out path);
        if (result >= 0) {
            try { return Marshal.PtrToStringUni(path); }
            finally { Marshal.FreeCoTaskMem(path); }
        }
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "My Games");
    }
}
'@
    $SavedGamesDirectory = [ReachSavedGames]::Resolve()
}
$session = Join-Path $package ('playtest-' + [Guid]::NewGuid().ToString('N'))
$profile = Join-Path $session 'profile'
$mod = Join-Path $profile 'reach_lab'
New-Item -ItemType Directory -Path $mod -Force | Out-Null
# The original save/profile tree is copied, never modified or used by the lab.
$originalProfile = Join-Path $SavedGamesDirectory 'id Software/DOOM 3 BFG'
if (Test-Path -LiteralPath $originalProfile -PathType Container) {
    $backup = Join-Path $session 'backup-original-profile'
    Copy-Item -LiteralPath $originalProfile -Destination $backup -Recurse
    Write-Host "Original profile snapshot: $backup"
}
Copy-Item -LiteralPath (Join-Path $package 'reach_prototype.cfg') -Destination (Join-Path $mod 'reach_prototype.cfg')
Set-Content -LiteralPath (Join-Path $mod 'autoexec.cfg') -Value 'exec reach_prototype.cfg' -Encoding ASCII
$startArguments = '+set fs_basepath "' + $install + '" +set fs_savepath "' + $profile +
    '" +set fs_game reach_lab +set com_allowConsole 1 +set r_fullscreen 0 +set com_skipIntroVideos 1 +set logFile 2 +set g_reachCombat 1 +set g_reachLabAutoConfig 1 +exec reach_prototype.cfg'
[ordered]@{ binary = $binary; data = $install; profile = $profile; originalProfile = $originalProfile; arguments = $startArguments } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $session 'launch-plan.json') -Encoding UTF8
Write-Host "Playtest session: $session"
Write-Host 'The game uses a new lab profile and reads BFG data from Steam. Existing executables and profiles are preserved.'
if ($PrepareOnly) { Write-Host 'Prepared only; no game was launched.'; return }
$process = Start-Process -FilePath $binary -WorkingDirectory $package -ArgumentList $startArguments -PassThru
$process.WaitForExit()
Write-Host "Game exit code: $($process.ExitCode)"
Write-Host "For troubleshooting, attach qconsole.log from $mod. Do not upload your backup or saves."
