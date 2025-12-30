$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = "python"
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
