from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path
    data_dir: Path
    logs_dir: Path
    exports_dir: Path
    db_path: Path


def get_paths() -> AppPaths:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        local = str(Path.home() / "AppData" / "Local")

    base = Path(local) / "klimozawr"
    data = base / "data"
    logs = base / "logs"
    exports = base / "exports"

    data.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)

    db_path = data / "klimozawr.db"
    return AppPaths(base_dir=base, data_dir=data, logs_dir=logs, exports_dir=exports, db_path=db_path)
