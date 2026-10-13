[CmdletBinding()]
param(
    [string]$BfgPath = 'C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition',
    [string]$SavedGamesDirectory = '',
    [switch]$Windowed,
    [switch]$FlushLog,
    [switch]$SingleThreaded,
    [switch]$StockCombat,
    [switch]$Diagnostics,
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
$binaryHash = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash
if ($binaryHash -ine $expected.sha256) {
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
$displayArguments = '+set r_fullscreen 0 +set r_windowWidth 1280 +set r_windowHeight 720'
if (-not $Windowed) {
    # Match the DPI-aware game executable when measuring the desktop.
    Add-Type @'
using System.Runtime.InteropServices;
public static class ReachDesktop {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
'@
    [ReachDesktop]::SetProcessDPIAware() | Out-Null
    Add-Type -AssemblyName System.Windows.Forms
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    if ($null -eq $screen) { throw 'No primary display was found. Try the launcher with -Windowed.' }
    $bounds = $screen.Bounds
    $displayArguments = '+set r_fullscreen -1 +set r_windowX ' + $bounds.X + ' +set r_windowY ' + $bounds.Y +
        ' +set r_windowWidth ' + $bounds.Width + ' +set r_windowHeight ' + $bounds.Height
    Write-Host "Display: borderless fullscreen, $($bounds.Width) x $($bounds.Height)"
}
$logMode = if ($FlushLog) { 2 } else { 1 }
$session = Join-Path $package ('playtest-' + [Guid]::NewGuid().ToString('N'))
$profile = Join-Path $session 'profile'
$mod = Join-Path $profile 'reach_lab'
$consoleLog = Join-Path $session 'qconsole.log'
New-Item -ItemType Directory -Path $mod -Force | Out-Null
# The original save/profile tree is copied, never modified or used by the lab.
$originalProfile = Join-Path $SavedGamesDirectory 'id Software/DOOM 3 BFG'
if (Test-Path -LiteralPath $originalProfile -PathType Container) {
    $backup = Join-Path $session 'backup-original-profile'
    Copy-Item -LiteralPath $originalProfile -Destination $backup -Recurse
    Write-Host "Original profile snapshot: $backup"
}
Copy-Item -LiteralPath (Join-Path $package 'reach_prototype.cfg') -Destination (Join-Path $mod 'reach_prototype.cfg')
$mode = if ($StockCombat) { 'stock-combat' } else { 'reach-combat' }
$threadMode = if ($SingleThreaded) { 'single-threaded' } else { 'normal-threading' }
$config = @('echo "[ReachDiag] binary ' + $binaryHash.Substring(0, 12) + ' ' + $mode + ' ' + $threadMode + '"')
if ($StockCombat) {
    $config += 'set g_reachCombat 0'
    $combatArguments = '+set g_reachCombat 0 +set g_reachLabAutoConfig 0'
} else {
    $config += 'exec reach_prototype.cfg'
    # autoexec and post-spawn loading already execute the prototype config.
    $combatArguments = '+set g_reachCombat 1 +set g_reachLabAutoConfig 1'
}
Set-Content -LiteralPath (Join-Path $mod 'autoexec.cfg') -Value $config -Encoding ASCII
$threadArguments = if ($SingleThreaded) {
    '+set com_smp 0 +set jobs_numThreads 0 +set r_useParallelAddModels 0 +set r_useParallelAddLights 0 +set r_useParallelAddShadows 0'
} else { '' }
$diagnosticMode = if ($Diagnostics) { 1 } else { 0 }
$startArguments = '+set fs_basepath "' + $install + '" +set fs_savepath "' + $profile +
    '" +set fs_game reach_lab +set com_allowConsole 1 ' + $displayArguments +
    ' +set com_skipIntroVideos 1 +set logFile ' + $logMode + ' +set logFileName "' + $consoleLog + '" +set com_timestampPrints 1' +
    ' +set com_reachDiagnostics ' + $diagnosticMode + ' ' + $threadArguments + ' ' + $combatArguments
# WinMain tokenizes the entire command line through idCmdArgs (64 arguments).
if ([regex]::Matches($startArguments, '"[^"]*"|\S+').Count -gt 64) {
    throw 'The launch arguments exceed the engine parser limit. Move optional settings into a config file.'
}
[ordered]@{ binary = $binary; binarySha256 = $binaryHash; mode = $mode; threading = $threadMode; data = $install; profile = $profile; originalProfile = $originalProfile; arguments = $startArguments } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $session 'launch-plan.json') -Encoding UTF8
Write-Host "Playtest session: $session"
Write-Host 'The game uses a new lab profile and reads BFG data from Steam. Existing executables and profiles are preserved.'
if ($PrepareOnly) { Write-Host 'Prepared only; no game was launched.'; return }
if ($Diagnostics) {
    try {
        [ordered]@{
            windows = [Environment]::OSVersion.VersionString
            processors = @(Get-CimInstance Win32_Processor -OperationTimeoutSec 5 | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
            graphics = @(Get-CimInstance Win32_VideoController -OperationTimeoutSec 5 | Select-Object Name, DriverVersion)
            memory = @(Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 5 | Select-Object TotalVisibleMemorySize, FreePhysicalMemory)
        } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $session 'hardware.json') -Encoding UTF8
    } catch { Write-Host "Hardware information unavailable: $($_.Exception.Message)" }
}
$launchTime = Get-Date
$process = Start-Process -FilePath $binary -WorkingDirectory $package -ArgumentList $startArguments -PassThru
$process.Handle | Out-Null
if ($Diagnostics) {
    while (-not $process.WaitForExit(2000)) {
        try {
            $process.Refresh()
            [ordered]@{ elapsedSeconds = [Math]::Round(((Get-Date) - $launchTime).TotalSeconds, 1); privateBytes = $process.PrivateMemorySize64; workingSetBytes = $process.WorkingSet64; responding = $process.Responding } |
                ConvertTo-Json -Compress | Add-Content (Join-Path $session 'process-health.jsonl') -Encoding UTF8
        } catch { Write-Host "Process sample unavailable: $($_.Exception.Message)" }
    }
} else { $process.WaitForExit() }
$exitCode = $process.ExitCode
$exitHex = '0x{0:X8}' -f [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$exitCode), 0)
$events = @()
if ($Diagnostics -and $exitCode -ne 0) {
    try {
        $events = @(Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000, 1001; StartTime = $launchTime } -ErrorAction Stop |
            Where-Object { $_.Message -match 'Doom3BFG\.exe' } | Select-Object -First 3 TimeCreated, Id, Message)
    } catch { Write-Host 'No matching Windows crash event was available at exit.' }
}
[ordered]@{ exitCode = $exitCode; exitCodeHex = $exitHex; elapsedSeconds = ((Get-Date) - $launchTime).TotalSeconds; events = $events } |
    ConvertTo-Json -Depth 5 | Set-Content (Join-Path $session 'exit-report.json') -Encoding UTF8
Write-Host "Game exit code: $exitCode ($exitHex)"
if ($Diagnostics) {
    # Include only diagnostics, never the backup, saves or installed game data.
    $report = Join-Path $session 'diagnostics'
    New-Item -ItemType Directory -Path $report | Out-Null
    foreach ($name in @('launch-plan.json', 'hardware.json', 'process-health.jsonl', 'exit-report.json')) {
        $source = Join-Path $session $name
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $report }
    }
    $consoleSources = @()
    if (Test-Path -LiteralPath $consoleLog) { $consoleSources += Get-Item -LiteralPath $consoleLog }
    # Older/default configs can place the log under base or an expansion folder.
    $consoleSources += @(Get-ChildItem -LiteralPath $profile -Filter 'qconsole.log' -File -Recurse)
    $consoleIndex = @()
    for ($i = 0; $i -lt $consoleSources.Count; $i++) {
        $name = if ($i -eq 0) { 'qconsole.log' } else { "qconsole-$i.log" }
        Copy-Item -LiteralPath $consoleSources[$i].FullName -Destination (Join-Path $report $name)
        $consoleIndex += [ordered]@{ reportName = $name; source = $consoleSources[$i].FullName }
    }
    ConvertTo-Json -InputObject $consoleIndex | Set-Content (Join-Path $report 'console-log-index.json') -Encoding UTF8
    if ($consoleSources.Count -eq 0) { Write-Host 'WARNING: No console log was found. The ZIP will contain process/exit information only.' }
    $zip = Join-Path $package ('reach-diagnostics-' + (Split-Path $session -Leaf) + '.zip')
    Compress-Archive -Path (Join-Path $report '*') -DestinationPath $zip
    Write-Host "Send this diagnostic ZIP: $zip"
}
Write-Host "Console log: $consoleLog. Do not upload your backup or saves."
