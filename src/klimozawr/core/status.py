from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

from klimozawr.core.models import StatusColor


def compute_loss_pct(successes: int, total: int = 3) -> int:
    if total <= 0:
        return 100
    lost = total - successes
    if lost <= 0:
        return 0
    if lost == 1:
        return 33
    if lost == 2:
        return 66
    return 100


def compute_status(
    now_utc: datetime,
    tick_has_success: bool,
    last_ok_utc: Optional[datetime],
    first_seen_utc: datetime,
    yellow_to_red_secs: int,
) -> StatusColor:
    if tick_has_success:
        return "GREEN"

    anchor = last_ok_utc or first_seen_utc
    down_for = now_utc - anchor
    if down_for <= timedelta(seconds=yellow_to_red_secs):
        return "YELLOW"
    return "RED"


def derive_tick_metrics(rtts_ms: list[int | None]) -> tuple[int, Optional[int], Optional[int], bool]:
    ok = [x for x in rtts_ms if isinstance(x, int)]
    loss_pct = compute_loss_pct(len(ok), total=len(rtts_ms))
    unstable = 0 < loss_pct < 100

    rtt_last = ok[-1] if ok else None
    rtt_avg = int(round(sum(ok) / len(ok))) if ok else None
    return loss_pct, rtt_last, rtt_avg, unstable
