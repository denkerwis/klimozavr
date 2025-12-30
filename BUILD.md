# Build (Windows EXE)

This project targets **Windows 10/11 + Python 3.12** and bundles a GUI app (PySide6) with PyInstaller.

## Prerequisites
- Python 3.12 installed and available in `PATH`
- Visual C++ runtime (required by PySide6 on Windows)

## Build steps
From the repository root:

```powershell
.\scripts\build_exe.ps1
```

The script will:
1. Create `.venv` if missing
2. Install dependencies
3. Generate required WAV assets
4. Run PyInstaller using `klimozawr.spec`

Output is placed in:
```
dist\klimozawr\klimozawr.exe
```

## Portable vs AppData mode
By default, the app stores runtime data in:
```
%APPDATA%\Klimozawr
```

To run in **portable mode** (store data рядом с `.exe`), set:
```powershell
$env:KLIMOZAWR_PORTABLE = "1"
.\dist\klimozawr\klimozawr.exe
```

This creates a `KlimozawrData` folder next to the executable.

## Smoke test
Run a minimal sanity check (starts the GUI briefly and exits):
```powershell
.\scripts\smoke_run.ps1
```

## PyInstaller + PySide6 notes
- Qt Multimedia depends on plugins; `klimozawr.spec` includes `PySide6.QtMultimedia` in `hiddenimports`.
- If multimedia is missing, verify that the PyInstaller hooks are active and that the `resources/` folder is bundled.
