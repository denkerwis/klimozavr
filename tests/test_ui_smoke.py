from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from klimozawr.config import AppPaths
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.migrations import apply_migrations
from klimozawr.storage.repositories import DeviceRepo
from klimozawr.ui import app_controller as app_controller_module
from klimozawr.ui.app_controller import AppController
from klimozawr.ui.windows.admin_main import AdminMainWindow
from klimozawr.ui.windows.user_main import UserMainWindow
from klimozawr.ui.widgets.device_cards import DeviceCardWidget


class DummySoundManager:
    def __init__(self, yellow_wav: Path, red_wav: Path) -> None:
        self.yellow_wav = yellow_wav
        self.red_wav = red_wav
        self.played: list[str] = []
        self.played_paths: list[str] = []

    def play(self, level: str) -> None:
        self.played.append(level)

    def play_path(self, wav_path: str, *, volume: float = 0.9) -> None:
        self.played_paths.append(wav_path)


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
    controller._admin_win = win
    win.show()

    qtbot.waitExposed(win)


def test_selection_updates_details(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(app_controller_module, "SoundManager", DummySoundManager)

    paths = _make_paths(tmp_path)
    db = SQLiteDatabase(paths.db_path)
    apply_migrations(db)

    controller = AppController(db=db, paths=paths)
    dr = DeviceRepo(db)
    _action, did = dr.upsert_device({
        "target": "10.0.0.5",
        "name": "switch",
        "comment": "",
        "location": "",
        "owner": "",
        "yellow_to_red_secs": 120,
        "yellow_notify_after_secs": 30,
        "ping_timeout_ms": 1000,
    })
    controller._reload_devices()

    win = AdminMainWindow()
    qtbot.addWidget(win)
    controller._admin_win = win
    controller._wire_common_window(win)
    controller._wire_admin_window(win)
    win.cards.set_devices(controller._snapshots_list())
    win.show()
    qtbot.waitExposed(win)

    controller._select_device(did)
    assert "switch" in win.details.host_label.text()


def test_user_window_smoke(qtbot):
    win = UserMainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)


def test_device_card_smoke(qtbot):
    card = DeviceCardWidget(device_id=1)
    qtbot.addWidget(card)
    card.set_snapshot({
        "device_id": 1,
        "target": "10.0.0.12",
        "name": "очень-длинное-имя-хоста-для-проверки-обрезания",
        "status": "GREEN",
        "loss_pct": 0,
        "rtt_last_ms": 12,
        "unstable": False,
    })
    card.show()
    qtbot.waitExposed(card)
