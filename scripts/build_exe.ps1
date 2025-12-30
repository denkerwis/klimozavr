$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$venvPath = Join-Path $repoRoot ".venv"
$py = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $py)) {
  Write-Host "== Creating venv (.venv) =="
  & python -m venv $venvPath
}

if (-not (Test-Path $py)) {
  throw "Python not found at: $py"
}

& $py --version

& $py -m pip install --upgrade pip

$pyproject = Join-Path $repoRoot "pyproject.toml"
$hasGuiExtra = $false
if (Test-Path $pyproject) {
  $hasGuiExtra = Select-String -Path $pyproject -Pattern "^\s*gui\s*=" -Quiet
}

$installTarget = if ($hasGuiExtra) { ".[gui]" } else { "." }
& $py -m pip install -e $installTarget
& $py -m pip install pyinstaller

Write-Host "== Checking default WAV assets =="
$defaultWavs = @(
  "resources\sounds\red.wav",
  "resources\sounds\yellow.wav",
  "resources\sounds\offline.wav",
  "resources\sounds\up.wav"
)
foreach ($wav in $defaultWavs) {
  $wavPath = Join-Path $repoRoot $wav
  if (-not (Test-Path $wavPath)) {
    Write-Warning "Missing default WAV: $wavPath"
  }
}

Write-Host "== Building EXE with PyInstaller (onedir) =="
& $py -m PyInstaller (Join-Path $repoRoot "klimozawr.spec") --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Build complete: $repoRoot\dist\klimozawr\klimozawr.exe"
