from __future__ import annotations

from datetime import datetime, timedelta, timezone

from klimozawr.core.models import Device
from klimozawr.core.monitor_engine import MonitorEngine


class DummyIcmpClient:
    def __init__(self, rtts: list[int | None]) -> None:
        self._rtts = rtts

    def ping_three(self, ip: str, timeout_ms: int) -> list[int | None]:
        return list(self._rtts)


def test_yellow_to_red_transition_triggers_alerts():
    engine = MonitorEngine(max_workers=1)
    device = Device(
        id=1,
        ip="127.0.0.1",
        name="test",
        comment="",
        location="",
        owner="",
        yellow_to_red_secs=1,
        yellow_notify_after_secs=0,
        ping_timeout_ms=100,
    )
    engine.set_devices([device])

    state = engine.get_state(device.id)
    assert state is not None

    base = datetime.now(timezone.utc)
    state.first_seen_utc = base

    alerts: list[str] = []
    engine.on_alert = lambda _did, level: alerts.append(level)

    client = DummyIcmpClient([None, None, None])

    engine._ping_device_tick(client, device, base)
    assert state.current_status == "YELLOW"

    engine._ping_device_tick(client, device, base + timedelta(seconds=2))
    assert state.current_status == "RED"
    assert state.red_start_utc is not None
    assert alerts == ["YELLOW", "RED"]
