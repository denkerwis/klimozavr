Write-Host "== Smoke check: default WAVs via resource_path =="

# Ensure src-layout imports work
$env:PYTHONPATH = "src"

$code = @'
from pathlib import Path
from klimozawr.config import resource_path

required = [
    "resources/sounds/red.wav",
    "resources/sounds/yellow.wav",
    "resources/sounds/offline.wav",
    "resources/sounds/up.wav",
]

missing = []
resolved = []

for rel in required:
    p = Path(resource_path(rel))
    resolved.append((rel, p))
    if not p.exists():
        missing.append(f"{rel} -> {p}")

if missing:
    raise SystemExit("Missing WAVs:\n" + "\n".join(missing))

print("OK: default WAVs present:")
for rel, p in resolved:
    print(" -", rel, "=>", p)
'@

$tmp = Join-Path $env:TEMP "klimozawr_smoke_wavs.py"
Set-Content -Path $tmp -Value $code -Encoding UTF8

python $tmp
$rc = $LASTEXITCODE

Remove-Item -Force $tmp -ErrorAction SilentlyContinue

if ($rc -ne 0) {
    throw "Smoke check failed (default WAVs missing or resource_path broken)."
}

Write-Host "Smoke check OK."
