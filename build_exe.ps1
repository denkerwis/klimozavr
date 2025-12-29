$ErrorActionPreference = "Stop"

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Error "venv not found. Run .\dev_setup.ps1 first."
}

# ensure wavs exist
& $py .\tools\generate_wavs.py

Write-Host "== Building EXE with PyInstaller (onedir) =="
& $py -m PyInstaller .\klimozawr.spec --noconfirm --clean

Write-Host "Build complete: .\dist\klimozawr\klimozawr.exe"
