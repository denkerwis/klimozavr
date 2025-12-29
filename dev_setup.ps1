$ErrorActionPreference = "Stop"

Write-Host "== klimozawr dev setup =="

if (-not (Test-Path ".\.venv")) {
  python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -e ".[dev]"

# generate sound assets deterministically
& $py .\tools\generate_wavs.py

Write-Host "Done. Run: .\run_gui.cmd"
