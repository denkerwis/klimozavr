from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("klimozawr.rotation")


@dataclass(frozen=True)
class RotationConfig:
    raw_keep_hours: int = 72
    agg_keep_days: int = 90
    events_keep_days: int = 90


def month_bucket(ts_utc: datetime) -> str:
    return f"{ts_utc.year:04d}-{ts_utc.month:02d}"


def export_rows_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run_daily_rotation(repo, exports_root: Path, cfg: RotationConfig) -> None:
    """
    repo must expose:
      - delete_raw_before(cutoff_utc)
      - select_agg_before(cutoff_utc) -> list[dict]
      - delete_agg_before(cutoff_utc)
      - select_events_before(cutoff_utc) -> list[dict]
      - delete_events_before(cutoff_utc)
    """
    now = datetime.now(timezone.utc)
    raw_cut = now - timedelta(hours=cfg.raw_keep_hours)
    old_cut = now - timedelta(days=cfg.agg_keep_days)

    logger.info("rotation start raw_cut=%s old_cut=%s", raw_cut.isoformat(), old_cut.isoformat())

    repo.delete_raw_before(raw_cut)

    agg_rows = repo.select_agg_before(old_cut)
    ev_rows = repo.select_events_before(old_cut)

    if agg_rows:
        b = month_bucket(old_cut)
        export_rows_csv(exports_root / b / "agg_minute.csv", list(agg_rows[0].keys()), agg_rows)
        repo.delete_agg_before(old_cut)

    if ev_rows:
        b = month_bucket(old_cut)
        export_rows_csv(exports_root / b / "events.csv", list(ev_rows[0].keys()), ev_rows)
        repo.delete_events_before(old_cut)

    logger.info("rotation done")
