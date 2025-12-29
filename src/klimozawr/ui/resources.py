from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    # src/klimozawr/ui/resources.py -> parents[3] is repo root in dev
    p = Path(__file__).resolve()
    root = p.parents[3]
    return root


def runtime_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return project_root()


def resource_path(rel: str) -> Path:
    return runtime_root() / rel
