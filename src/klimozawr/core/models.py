from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

StatusColor = Literal["GREEN", "YELLOW", "RED"]


@dataclass(frozen=True)
class Device:
    id: int
    ip: str
    name: str
    comment: str
    location: str
    owner: str
    yellow_to_red_secs: int
    yellow_notify_after_secs: int
    ping_timeout_ms: int


@dataclass(frozen=True)
class TickResult:
    device_id: int
    ts_utc: datetime
    loss_pct: int              # 0/33/66/100
    rtt_last_ms: Optional[int] # last successful RTT
    rtt_avg_ms: Optional[int]  # avg over successful in tick
    unstable: bool             # 33 or 66
    status: StatusColor        # GREEN/YELLOW/RED


@dataclass
class DeviceRuntimeState:
    device_id: int
    first_seen_utc: datetime
    last_ok_utc: Optional[datetime] = None

    # for “episodes”
    yellow_start_utc: Optional[datetime] = None
    red_start_utc: Optional[datetime] = None

    yellow_acked: bool = False
    red_acked: bool = False

    last_yellow_alert_utc: Optional[datetime] = None
    last_red_alert_utc: Optional[datetime] = None

    current_status: Optional[StatusColor] = None
    current_unstable: bool = False
