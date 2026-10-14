$ErrorActionPreference = 'Stop'
$output = Join-Path (Get-Location) 'build/ReachDebugLog.exe'
New-Item -ItemType Directory -Path (Split-Path $output) -Force | Out-Null
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /target:exe /platform:x64 ('/out:' + $output) (Join-Path $PSScriptRoot 'ReachDebugLog.cs')
if ($LASTEXITCODE -ne 0) { throw 'Debug-output capture compiler failed.' }

$root = Join-Path $env:RUNNER_TEMP ('Reach Debug Capture ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -Force | Out-Null
$fixture = Join-Path $root 'RBDoom3BFG.exe'
Add-Type -OutputAssembly $fixture -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
public static class DebugOutputFixture {
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi)]
    public static extern void OutputDebugString(string text);
    public static int Main(string[] args) {
        if (args.Length == 1 && args[0] == "--foreign") {
            OutputDebugString("FOREIGN_PROCESS_MUST_NOT_BE_COLLECTED\n");
            return 0;
        }
        File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "arguments.txt"), String.Join("\n", args));
        Thread background = new Thread(delegate() { OutputDebugString("[ReachSwitch r2] background weapon marker\n"); });
        background.Start();
        background.Join();
        ProcessStartInfo other = new ProcessStartInfo(Process.GetCurrentProcess().MainModule.FileName, "--foreign");
        other.UseShellExecute = false;
        using (Process foreign = Process.Start(other)) { foreign.WaitForExit(); }
        OutputDebugString("[ReachSwitch r2] final weapon marker\n");
        return 0;
    }
}
'@
$log = Join-Path $root 'captured debug.log'
$arguments = @('+set', 'fs_game', 'reach', 'space path value', 'quote"value', 'trailing backslash\')
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $output
# Explicit Windows argv quoting avoids PowerShell 5.1's native quote removal.
$start.Arguments = '"' + $fixture + '" "' + $log + '" +set fs_game reach "space path value" "quote\"value" "trailing backslash\\"'
$start.UseShellExecute = $false
$process = [System.Diagnostics.Process]::Start($start)
if (-not $process.WaitForExit(15000)) { $process.Kill(); throw 'Debug-output fixture timed out.' }
if ($process.ExitCode -ne 0) { throw 'Debug-output capture fixture failed.' }
$captured = Get-Content -Raw -LiteralPath $log
if (-not $captured.Contains('[ReachSwitch r2] background weapon marker') -or -not $captured.Contains('[ReachSwitch r2] final weapon marker')) { throw 'Missing actual Windows debug-output markers, including background-thread output.' }
if ($captured.Contains('FOREIGN_PROCESS_MUST_NOT_BE_COLLECTED')) { throw 'Captured another process output.' }
if ((Get-Content -Raw -LiteralPath (Join-Path $root 'arguments.txt')) -ne ($arguments -join "`n")) { throw 'Capture helper modified game arguments.' }
Write-Host '::notice title=Debug output capture::PASS: actual Windows background-thread markers flushed, final marker retained, foreign PID excluded, argument quoting preserved'
