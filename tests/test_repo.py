from pathlib import Path
import tempfile

from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.migrations import apply_migrations
from klimozawr.storage.repositories import UserRepo, DeviceRepo


def test_user_flow_and_device_upsert():
    with tempfile.TemporaryDirectory() as td:
        dbp = Path(td) / "t.db"
        db = SQLiteDatabase(dbp)
        apply_migrations(db)

        ur = UserRepo(db)
        assert ur.count_users() == 0
        ur.create_user("admin", "pass", "admin")
        assert ur.count_users() == 1
        assert ur.verify_login("admin", "pass") is not None
        assert ur.verify_login("admin", "bad") is None

        dr = DeviceRepo(db)
        action, did = dr.upsert_device({
            "target": "192.168.0.1",
            "name": "router",
            "comment": "",
            "location": "",
            "owner": "",
            "yellow_to_red_secs": 120,
            "yellow_notify_after_secs": 30,
            "ping_timeout_ms": 1000,
            "icon_path": "icon.png",
            "icon_scale": 120,
            "sound_down_path": "down.wav",
            "sound_up_path": "up.wav",
        })
        assert action == "added"
        action2, did2 = dr.upsert_device({
            "target": "192.168.0.1",
            "name": "router2",
            "comment": "x",
            "location": "lab",
            "owner": "me",
            "yellow_to_red_secs": 90,
            "yellow_notify_after_secs": 10,
            "ping_timeout_ms": 500,
            "icon_path": "icon2.png",
            "icon_scale": 90,
            "sound_down_path": "down2.wav",
            "sound_up_path": "up2.wav",
        })
        assert action2 == "updated"
        assert did == did2
        devices = dr.list_devices()
        assert len(devices) == 1
        assert devices[0].icon_path == "icon2.png"
        assert devices[0].icon_scale == 90
        assert devices[0].sound_down_path == "down2.wav"
        assert devices[0].sound_up_path == "up2.wav"
