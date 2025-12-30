$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = "python"
}

$resourceCheck = @'
from pathlib import Path

from klimozawr.config import resource_path

paths = [
    Path(resource_path("resources/sounds/red.wav")),
    Path(resource_path("resources/sounds/yellow.wav")),
    Path(resource_path("resources/sounds/offline.wav")),
    Path(resource_path("resources/sounds/up.wav")),
]
missing = [p for p in paths if not p.exists()]
if missing:
    raise SystemExit(f"Missing default WAV(s): {', '.join(str(p) for p in missing)}")
print("Default WAVs found:", ", ".join(str(p) for p in paths))
'@

Write-Host "== Smoke check: default WAVs via resource_path =="
& $py -c $resourceCheck
if ($LASTEXITCODE -ne 0) {
  throw "Smoke check failed (default WAVs missing)."
}

Write-Host "== Smoke run: python -m klimozawr (7s) =="
$proc = Start-Process -FilePath $py -ArgumentList "-m", "klimozawr" -PassThru
Start-Sleep -Seconds 7

if (-not $proc.HasExited) {
  $null = $proc.CloseMainWindow()
  Start-Sleep -Seconds 2
}

if (-not $proc.HasExited) {
  Stop-Process -Id $proc.Id -Force
}

Write-Host "Smoke run completed."
