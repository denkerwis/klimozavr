$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$venvPath = Join-Path $repoRoot ".venv"
$py = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $py)) {
  Write-Host "== Creating venv (.venv) =="
  & python -m venv $venvPath
}

& $py -m pip install --upgrade pip

$pyproject = Join-Path $repoRoot "pyproject.toml"
$hasGuiExtra = $false
if (Test-Path $pyproject) {
  $hasGuiExtra = Select-String -Path $pyproject -Pattern "^\s*gui\s*=" -Quiet
}

$installTarget = if ($hasGuiExtra) { ".[gui]" } else { "." }
& $py -m pip install -e $installTarget
& $py -m pip install pyinstaller

Write-Host "== Building EXE with PyInstaller (onedir) =="
& $py -m PyInstaller (Join-Path $repoRoot "klimozawr.spec") --noconfirm --clean

Write-Host "Build complete: $repoRoot\dist\klimozawr\klimozawr.exe"
