$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('Reach Direct Launch ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $root 'reach') -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'Play-Reach.cmd') $root
Copy-Item (Join-Path $PSScriptRoot 'Play-Reach-diagnostic.cmd') $root
Copy-Item (Join-Path (Get-Location) 'build/ReachDebugLog.exe') $root
Set-Content (Join-Path $root 'reach/zzz_reach_ar.pk4') 'fixture only'
Set-Content (Join-Path $root 'reach/zzzz_reach_switch.pk4') 'fixture only'
$exe = Join-Path $root 'RBDoom3BFG.exe'
Add-Type -OutputAssembly $exe -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.IO;
public static class ReachDirectLaunch {
    public static int Main(string[] args) {
        File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "launch-fixture.txt"), Environment.CurrentDirectory + "\n" + String.Join("\n", args));
        return 0;
    }
}
'@
& cmd.exe /d /c ('"' + (Join-Path $root 'Play-Reach.cmd') + '"')
if ($LASTEXITCODE -ne 0) { throw 'Direct CMD launcher failed.' }
$report = Join-Path $root 'launch-fixture.txt'
$deadline = (Get-Date).AddSeconds(10)
while (-not (Test-Path -LiteralPath $report) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path -LiteralPath $report)) { throw 'Direct launcher did not start the fixture executable.' }
$lines = @(Get-Content $report)
if ($lines.Count -ne 4 -or $lines[0] -ne $root -or $lines[1] -ne '+set' -or $lines[2] -ne 'fs_game' -or $lines[3] -ne 'reach') { throw 'Direct launcher changed working directory or supplied unexpected engine settings.' }
Write-Host '::notice title=Direct RBDoom launcher::PASS: directly launched a fixture executable with only fs_game reach; no game or PowerShell play harness launched'
Remove-Item $report
& cmd.exe /d /c ('"' + (Join-Path $root 'Play-Reach-diagnostic.cmd') + '" --no-explorer')
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic CMD launcher failed.' }
if (-not (Test-Path -LiteralPath $report)) { throw 'Diagnostic launcher did not start and wait for the fixture executable.' }
$lines = @(Get-Content $report)
$expected = @($root, '+set', 'fs_game', 'reach', '+set', 'logFileName', (Join-Path $env:TEMP 'Reach-weapon-switch.log'), '+set', 'logFile', '2', '+set', 'g_debugWeapon', '1')
if (($lines -join "`n") -ne ($expected -join "`n")) { throw 'Diagnostic launcher changed working directory or supplied unexpected engine settings.' }
Write-Host '::notice title=Switch diagnostic launcher::PASS: debug-output reader launched and waited for fixture executable; mod selection, absolute log path and logging flags only'
