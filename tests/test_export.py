from __future__ import annotations

from datetime import datetime, timezone
from klimozawr.core.models import TickResult
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.migrations import apply_migrations
from klimozawr.storage.repositories import DeviceRepo, TelemetryRepo


def test_export_logs_csv(tmp_path):
    db = SQLiteDatabase(tmp_path / "test.db")
    apply_migrations(db)

    dr = DeviceRepo(db)
    _action, did = dr.upsert_device({
        "ip": "192.168.1.10",
        "name": "router",
        "comment": "",
        "location": "",
        "owner": "",
        "yellow_to_red_secs": 120,
        "yellow_notify_after_secs": 30,
        "ping_timeout_ms": 1000,
    })

    tr = TickResult(
        device_id=did,
        ts_utc=datetime.now(timezone.utc),
        loss_pct=0,
        rtt_last_ms=10,
        rtt_avg_ms=12,
        unstable=False,
        status="GREEN",
    )
    telemetry = TelemetryRepo(db)
    telemetry.insert_tick(tr)

    export_path = tmp_path / "logs.csv"
    telemetry.export_raw_csv(export_path, device_id=did)

    text = export_path.read_text(encoding="utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]
    assert lines[0].startswith("ts_utc,device_id,loss_pct")
    assert len(lines) >= 2
