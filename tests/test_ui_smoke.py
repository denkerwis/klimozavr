from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from klimozawr.config import AppPaths
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.migrations import apply_migrations
from klimozawr.ui import app_controller as app_controller_module
from klimozawr.ui.app_controller import AppController
from klimozawr.ui.windows.admin_main import AdminMainWindow
from klimozawr.ui.windows.user_main import UserMainWindow


class DummySoundManager:
    def __init__(self, yellow_wav: Path, red_wav: Path) -> None:
        self.yellow_wav = yellow_wav
        self.red_wav = red_wav
        self.played: list[str] = []

    def play(self, level: str) -> None:
        self.played.append(level)


def _make_paths(tmp_path: Path) -> AppPaths:
    base = tmp_path / "klimozawr"
    data = base / "data"
    logs = base / "logs"
    exports = base / "exports"
    data.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    return AppPaths(
        base_dir=base,
        data_dir=data,
        logs_dir=logs,
        exports_dir=exports,
        db_path=data / "klimozawr.db",
    )


def test_admin_window_smoke(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(app_controller_module, "SoundManager", DummySoundManager)

    paths = _make_paths(tmp_path)
    db = SQLiteDatabase(paths.db_path)
    apply_migrations(db)

    controller = AppController(db=db, paths=paths)

    win = AdminMainWindow()
    qtbot.addWidget(win)
    controller._wire_common_window(win)
    controller._wire_admin_window(win)
    win.show()

    qtbot.waitExposed(win)


def test_user_window_smoke(qtbot):
    win = UserMainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
