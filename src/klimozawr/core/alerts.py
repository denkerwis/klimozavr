from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Literal

AlertLevel = Literal["YELLOW", "RED"]


@dataclass(frozen=True)
class AlertDecision:
    fire: bool
    level: Optional[AlertLevel] = None
    reason: str = ""


YELLOW_REPEAT = timedelta(minutes=2)
RED_REPEAT = timedelta(minutes=5)


def should_fire_yellow(
    now_utc: datetime,
    yellow_start_utc: Optional[datetime],
    yellow_notify_after_secs: int,
    last_fired_utc: Optional[datetime],
    acked: bool,
) -> AlertDecision:
    if acked or yellow_start_utc is None:
        return AlertDecision(False)

    since_start = now_utc - yellow_start_utc
    if since_start < timedelta(seconds=yellow_notify_after_secs):
        return AlertDecision(False)

    if last_fired_utc is None:
        return AlertDecision(True, "YELLOW", "yellow notify threshold reached")

    if (now_utc - last_fired_utc) >= YELLOW_REPEAT:
        return AlertDecision(True, "YELLOW", "yellow repeat interval reached")

    return AlertDecision(False)


def should_fire_red(
    now_utc: datetime,
    red_start_utc: Optional[datetime],
    last_fired_utc: Optional[datetime],
    acked: bool,
) -> AlertDecision:
    if acked or red_start_utc is None:
        return AlertDecision(False)

    # immediate on entry
    if last_fired_utc is None:
        return AlertDecision(True, "RED", "red entered")

    if (now_utc - last_fired_utc) >= RED_REPEAT:
        return AlertDecision(True, "RED", "red repeat interval reached")

    return AlertDecision(False)
