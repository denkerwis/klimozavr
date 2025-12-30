from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path
    data_dir: Path
    logs_dir: Path
    exports_dir: Path
    db_path: Path


def _portable_enabled() -> bool:
    raw = os.environ.get("KLIMOZAWR_PORTABLE", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_paths() -> AppPaths:
    if _portable_enabled():
        base = _app_root() / "KlimozawrData"
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")
        base = Path(appdata) / "Klimozawr"
    data = base / "data"
    logs = base / "logs"
    exports = base / "exports"

    data.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)

    db_path = data / "klimozawr.db"
    return AppPaths(base_dir=base, data_dir=data, logs_dir=logs, exports_dir=exports, db_path=db_path)
