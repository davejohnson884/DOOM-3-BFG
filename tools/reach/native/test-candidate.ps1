$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('Reach Projection Launch ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $root 'reach') -Force | Out-Null
$env:REACH_NATIVE_FIXTURE_ROOT = $root
@'
import os, sys
from pathlib import Path
sys.path.insert(0, 'tools/reach/native')
import build_candidate as b
root = Path(os.environ['REACH_NATIVE_FIXTURE_ROOT'])
(root/'Play-Reach-projection.cmd').write_bytes(b.launcher())
(root/'Play-Reach-projection-diagnostic.cmd').write_bytes(b.launcher(True))
(root/'reach/zzzzz_reach_projection.pk4').write_bytes(b.overlay())
(root/'reach/zzz_reach_ar.pk4').write_text('fixture only')
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'Candidate launcher fixture generation failed.' }
Copy-Item -LiteralPath (Join-Path (Get-Location) 'build/ReachDebugLog.exe') -Destination $root
$exe = Join-Path $root 'ReachRBDoom3BFG.exe'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$code = Join-Path $root 'fixture.cs'
@'
using System;
using System.IO;
public static class CandidateLaunchFixture {
    public static int Main(string[] args) {
        File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "arguments.txt"),
            Environment.CurrentDirectory + "\n" + String.Join("\n", args));
        return 0;
    }
}
'@ | Set-Content -LiteralPath $code
& $compiler /nologo /platform:x64 /target:exe ('/out:' + $exe) $code
if ($LASTEXITCODE -ne 0) { throw 'Candidate launcher fixture compiler failed.' }
& cmd.exe /d /c ('"' + (Join-Path $root 'Play-Reach-projection.cmd') + '"')
if ($LASTEXITCODE -ne 0) { throw 'Candidate launcher failed.' }
$report = Join-Path $root 'arguments.txt'
$deadline = (Get-Date).AddSeconds(10)
while (-not (Test-Path -LiteralPath $report) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path -LiteralPath $report)) { throw 'Candidate launcher did not start the fixture.' }
$expected = @($root, '+set', 'fs_game', 'reach', '+exec', 'reach_projection.cfg')
if ((Get-Content -Raw -LiteralPath $report) -ne ($expected -join "`n")) { throw 'Candidate changed working directory or engine arguments.' }
Remove-Item -LiteralPath $report
& cmd.exe /d /c ('"' + (Join-Path $root 'Play-Reach-projection-diagnostic.cmd') + '" --no-explorer')
if ($LASTEXITCODE -ne 0) { throw 'Candidate diagnostic launcher failed.' }
$expected = @($root, '+set', 'fs_game', 'reach', '+set', 'logFileName', (Join-Path $env:TEMP 'Reach-weapon-switch.log'), '+set', 'logFile', '2', '+set', 'g_debugWeapon', '1', '+exec', 'reach_projection.cfg')
if ((Get-Content -Raw -LiteralPath $report) -ne ($expected -join "`n")) { throw 'Candidate diagnostic changed engine arguments.' }
Write-Host '::notice title=Projection launchers::PASS: candidate executable, working directory and config preserved through direct and diagnostic CMD launch'
