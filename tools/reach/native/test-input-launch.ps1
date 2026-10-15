$ErrorActionPreference = 'Stop'
try {
  $root = Join-Path $env:RUNNER_TEMP ('Reach Input Test ' + [Guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory (Join-Path $root 'reach') -Force | Out-Null
  $env:REACH_INPUT_FIXTURE = $root
  @'
import os,sys
from pathlib import Path
sys.path.insert(0,'tools/reach/native')
import build_combat as b
root=Path(os.environ['REACH_INPUT_FIXTURE'])
for diagnostic in [False,True]:
    name='Play-Reach-projection'+('-diagnostic' if diagnostic else '')+'.cmd'
    (root/name).write_bytes(b.launcher(diagnostic))
for name in ['zzz_reach_ar.pk4','zzzzzzz_reach_ar_pose.pk4','zzzzz_reach_projection.pk4']:
    (root/'reach'/name).write_bytes(b'old fixture only')
(root/b.PK4_PATH).write_bytes(b.overlay())
(root/b.CONFIG_PATH).write_bytes((b.ROOT.parent/'position/reach_pose.cfg').read_bytes())
(root/'reach/reach_controls_r14.cfg').write_bytes(b.CONTROLS)
'@ | python -
  if ($LASTEXITCODE -ne 0) { throw 'Input fixture generation failed.' }
  Copy-Item build/ReachDebugLog.exe $root
  $compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
  $code = Join-Path (Get-Location) 'build/reach-input-fixture.cs'
  $binary = Join-Path (Get-Location) 'build/ReachInputFixture.exe'
  @'
using System;
using System.IO;
public static class ReachInputFixture {
  public static int Main(string[] args) {
    File.WriteAllLines(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"input-args.txt"),args);
    return 0;
  }
}
'@ | Set-Content -LiteralPath $code
  & $compiler /nologo /platform:x64 /target:exe ('/out:'+$binary) $code
  if ($LASTEXITCODE -ne 0) { throw 'Input fixture compile failed.' }
  Copy-Item $binary (Join-Path $root 'ReachRBDoom3BFG.exe')
  foreach ($diagnostic in @($false,$true)) {
    $name = if ($diagnostic) { 'Play-Reach-projection-diagnostic.cmd' } else { 'Play-Reach-projection.cmd' }
    $extra = if ($diagnostic) { ' --no-explorer' } else { '' }
    & cmd.exe /d /c ('"' + (Join-Path $root $name) + '"' + $extra)
    if ($LASTEXITCODE -ne 0) { throw 'r14 launcher failed.' }
    $report = Join-Path $root 'input-args.txt'
    $deadline = (Get-Date).AddSeconds(10)
    while (-not (Test-Path $report) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path $report)) { throw 'r14 executable was not started.' }
    $arguments = @(Get-Content $report)
    if (($arguments[-4..-1] -join '|') -ne '+exec|reach_pose.cfg|+exec|reach_controls_r14.cfg') { throw 'Input bindings are not loaded after pose config.' }
    Remove-Item $report
  }
  Remove-Item (Join-Path $root 'reach/zzzzzzzzz_reach_input.pk4')
  & cmd.exe /d /c ('"' + (Join-Path $root 'Play-Reach-projection.cmd') + '" <NUL')
  if ($LASTEXITCODE -eq 0 -or (Test-Path (Join-Path $root 'input-args.txt'))) { throw 'Incomplete r14 copy started the engine.' }
  Write-Host '::notice title=Native input launch::PASS: real CMD and diagnostic helper load versioned controls last, support paths with spaces and reject a missing r14 PK4.'
  exit 0
} catch {
  $detail = $_.ToString().Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
  Write-Host "::error title=Native input launch::$detail"
  exit 1
}
