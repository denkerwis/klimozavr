from __future__ import annotations

import csv
import ipaddress
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from argon2 import PasswordHasher, exceptions as argon2_exc

from klimozawr.core.models import Device, TickResult
from klimozawr.storage.db import SQLiteDatabase

logger = logging.getLogger("klimozawr.repo")
ph = PasswordHasher()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass(frozen=True)
class ImportReport:
    added: int
    updated: int
    skipped: int
    reasons: list[str]


class UserRepo:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def count_users(self) -> int:
        c = self.db.connect().execute("SELECT COUNT(*) AS n FROM users;").fetchone()
        return int(c["n"])

    def list_users(self) -> list[dict]:
        rows = self.db.connect().execute(
            "SELECT id, username, role, created_at_utc FROM users ORDER BY id;"
        ).fetchall()
        return [dict(r) for r in rows]

    def create_user(self, username: str, password: str, role: str) -> int:
        h = ph.hash(password)
        conn = self.db.connect()
        conn.execute(
            "INSERT INTO users(username, password_hash, role, created_at_utc) VALUES (?,?,?,?);",
            (username, h, role, utc_now_iso()),
        )
        rid = conn.execute("SELECT last_insert_rowid() AS id;").fetchone()["id"]
        return int(rid)

    def delete_user(self, user_id: int) -> None:
        self.db.connect().execute("DELETE FROM users WHERE id=?;", (user_id,))

    def update_role(self, user_id: int, role: str) -> None:
        self.db.connect().execute("UPDATE users SET role=? WHERE id=?;", (role, user_id))

    def set_password(self, user_id: int, password: str) -> None:
        h = ph.hash(password)
        self.db.connect().execute("UPDATE users SET password_hash=? WHERE id=?;", (h, user_id))

    def verify_login(self, username: str, password: str) -> Optional[dict]:
        row = self.db.connect().execute(
            "SELECT id, username, password_hash, role FROM users WHERE username=?;",
            (username,),
        ).fetchone()
        if not row:
            return None
        try:
            ok = ph.verify(row["password_hash"], password)
        except argon2_exc.VerifyMismatchError:
            return None
        except Exception:
            logger.exception("argon2 verify error")
            return None
        if not ok:
            return None
        return {"id": int(row["id"]), "username": row["username"], "role": row["role"]}


class DeviceRepo:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def list_devices(self) -> list[Device]:
        rows = self.db.connect().execute("SELECT * FROM devices ORDER BY id;").fetchall()
        out: list[Device] = []
        for r in rows:
            out.append(
                Device(
                    id=int(r["id"]),
                    ip=r["ip"],
                    name=r["name"],
                    comment=r["comment"],
                    location=r["location"],
                    owner=r["owner"],
                    yellow_to_red_secs=int(r["yellow_to_red_secs"]),
                    yellow_notify_after_secs=int(r["yellow_notify_after_secs"]),
                    ping_timeout_ms=int(r["ping_timeout_ms"]),
                )
            )
        return out

    def upsert_device(self, d: dict, *, is_update_event: bool = True) -> tuple[str, int]:
        """
        Returns (action, device_id) where action in ('added','updated')
        """
        ip = d["ip"].strip()
        ipaddress.ip_address(ip)

        now = utc_now_iso()
        conn = self.db.connect()
        row = conn.execute("SELECT id FROM devices WHERE ip=?;", (ip,)).fetchone()
        if row:
            did = int(row["id"])
            conn.execute(
                """
                UPDATE devices SET
                  name=?, comment=?, location=?, owner=?,
                  yellow_to_red_secs=?, yellow_notify_after_secs=?, ping_timeout_ms=?,
                  updated_at_utc=?
                WHERE id=?;
                """,
                (
                    d.get("name", ""),
                    d.get("comment", ""),
                    d.get("location", ""),
                    d.get("owner", ""),
                    int(d.get("yellow_to_red_secs", 120)),
                    int(d.get("yellow_notify_after_secs", 30)),
                    int(d.get("ping_timeout_ms", 1000)),
                    now,
                    did,
                ),
            )
            if is_update_event:
                conn.execute(
                    "INSERT INTO events(ts_utc, device_id, kind, detail) VALUES (?,?,?,?);",
                    (now, did, "device_updated", f"device updated by ip={ip}"),
                )
            return ("updated", did)

        conn.execute(
            """
            INSERT INTO devices(
              ip, name, comment, location, owner,
              yellow_to_red_secs, yellow_notify_after_secs, ping_timeout_ms,
              created_at_utc, updated_at_utc
            ) VALUES (?,?,?,?,?,?,?,?,?,?);
            """,
            (
                ip,
                d.get("name", ""),
                d.get("comment", ""),
                d.get("location", ""),
                d.get("owner", ""),
                int(d.get("yellow_to_red_secs", 120)),
                int(d.get("yellow_notify_after_secs", 30)),
                int(d.get("ping_timeout_ms", 1000)),
                now,
                now,
            ),
        )
        did = int(conn.execute("SELECT last_insert_rowid() AS id;").fetchone()["id"])
        conn.execute(
            "INSERT INTO events(ts_utc, device_id, kind, detail) VALUES (?,?,?,?);",
            (now, did, "device_added", f"device added ip={ip}"),
        )
        return ("added", did)

    def delete_device(self, device_id: int) -> None:
        conn = self.db.connect()
        conn.execute(
            "INSERT INTO events(ts_utc, device_id, kind, detail) VALUES (?,?,?,?);",
            (utc_now_iso(), device_id, "device_deleted", "device deleted"),
        )
        conn.execute("DELETE FROM devices WHERE id=?;", (device_id,))

    def export_devices_csv(self, path: Path) -> None:
        devices = self.list_devices()
        headers = [
            "ip","name","comment","location","owner",
            "yellow_to_red_secs","yellow_notify_after_secs","ping_timeout_ms",
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for d in devices:
                w.writerow({
                    "ip": d.ip,
                    "name": d.name,
                    "comment": d.comment,
                    "location": d.location,
                    "owner": d.owner,
                    "yellow_to_red_secs": d.yellow_to_red_secs,
                    "yellow_notify_after_secs": d.yellow_notify_after_secs,
                    "ping_timeout_ms": d.ping_timeout_ms,
                })

    def import_devices_csv(self, path: Path, max_devices: int = 20) -> ImportReport:
        conn = self.db.connect()
        existing_count = conn.execute("SELECT COUNT(*) AS n FROM devices;").fetchone()["n"]
        existing_count = int(existing_count)

        added = updated = skipped = 0
        reasons: list[str] = []

        with path.open("r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for i, row in enumerate(r, start=2):
                try:
                    ip = (row.get("ip") or "").strip()
                    if not ip:
                        skipped += 1
                        reasons.append(f"line {i}: missing ip")
                        continue

                    # enforce cap
                    is_existing = conn.execute("SELECT 1 FROM devices WHERE ip=?;", (ip,)).fetchone() is not None
                    if not is_existing and (existing_count + added) >= max_devices:
                        skipped += 1
                        reasons.append(f"line {i}: device limit {max_devices} reached")
                        continue

                    payload = {
                        "ip": ip,
                        "name": (row.get("name") or "").strip(),
                        "comment": (row.get("comment") or "").strip(),
                        "location": (row.get("location") or "").strip(),
                        "owner": (row.get("owner") or "").strip(),
                        "yellow_to_red_secs": int((row.get("yellow_to_red_secs") or 120)),
                        "yellow_notify_after_secs": int((row.get("yellow_notify_after_secs") or 30)),
                        "ping_timeout_ms": int((row.get("ping_timeout_ms") or 1000)),
                    }
                    action, _did = self.upsert_device(payload, is_update_event=True)
                    if action == "added":
                        added += 1
                    else:
                        updated += 1
                except Exception as e:
                    skipped += 1
                    reasons.append(f"line {i}: {type(e).__name__}: {e}")

        return ImportReport(added=added, updated=updated, skipped=skipped, reasons=reasons)


class TelemetryRepo:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def insert_tick(self, tr: TickResult) -> None:
        self.db.connect().execute(
            """
            INSERT INTO raw_tick(device_id, ts_utc, loss_pct, rtt_last_ms, rtt_avg_ms, status, unstable)
            VALUES (?,?,?,?,?,?,?);
            """,
            (
                tr.device_id,
                tr.ts_utc.isoformat(),
                tr.loss_pct,
                tr.rtt_last_ms,
                tr.rtt_avg_ms,
                tr.status,
                1 if tr.unstable else 0,
            ),
        )

    def insert_event(self, ts_utc: datetime, device_id: Optional[int], kind: str, detail: str) -> None:
        self.db.connect().execute(
            "INSERT INTO events(ts_utc, device_id, kind, detail) VALUES (?,?,?,?);",
            (ts_utc.isoformat(), device_id, kind, detail),
        )

    def select_raw_range(self, device_id: int, since_utc: datetime) -> list[dict]:
        rows = self.db.connect().execute(
            """
            SELECT ts_utc, loss_pct, rtt_avg_ms
            FROM raw_tick
            WHERE device_id=? AND ts_utc >= ?
            ORDER BY ts_utc;
            """,
            (device_id, since_utc.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    def select_agg_range(self, device_id: int, since_utc: datetime) -> list[dict]:
        rows = self.db.connect().execute(
            """
            SELECT minute_ts_utc, loss_avg, avg_rtt_ms
            FROM agg_minute
            WHERE device_id=? AND minute_ts_utc >= ?
            ORDER BY minute_ts_utc;
            """,
            (device_id, since_utc.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_minute_agg(
        self,
        device_id: int,
        minute_ts_utc: datetime,
        avg_rtt_ms: Optional[float],
        max_rtt_ms: Optional[int],
        loss_avg: float,
        uptime_ratio: float,
    ) -> None:
        self.db.connect().execute(
            """
            INSERT INTO agg_minute(device_id, minute_ts_utc, avg_rtt_ms, max_rtt_ms, loss_avg, uptime_ratio)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(device_id, minute_ts_utc) DO UPDATE SET
              avg_rtt_ms=excluded.avg_rtt_ms,
              max_rtt_ms=excluded.max_rtt_ms,
              loss_avg=excluded.loss_avg,
              uptime_ratio=excluded.uptime_ratio;
            """,
            (
                device_id,
                minute_ts_utc.isoformat(),
                avg_rtt_ms,
                max_rtt_ms,
                loss_avg,
                uptime_ratio,
            ),
        )

    # rotation helpers
    def delete_raw_before(self, cutoff_utc: datetime) -> None:
        self.db.connect().execute("DELETE FROM raw_tick WHERE ts_utc < ?;", (cutoff_utc.isoformat(),))

    def select_agg_before(self, cutoff_utc: datetime) -> list[dict]:
        rows = self.db.connect().execute(
            "SELECT * FROM agg_minute WHERE minute_ts_utc < ? ORDER BY minute_ts_utc;",
            (cutoff_utc.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_agg_before(self, cutoff_utc: datetime) -> None:
        self.db.connect().execute("DELETE FROM agg_minute WHERE minute_ts_utc < ?;", (cutoff_utc.isoformat(),))

    def select_events_before(self, cutoff_utc: datetime) -> list[dict]:
        rows = self.db.connect().execute(
            "SELECT * FROM events WHERE ts_utc < ? ORDER BY ts_utc;",
            (cutoff_utc.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_events_before(self, cutoff_utc: datetime) -> None:
        self.db.connect().execute("DELETE FROM events WHERE ts_utc < ?;", (cutoff_utc.isoformat(),))


class AlertRepo:
    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def list_active_alerts(self) -> list[dict]:
        rows = self.db.connect().execute(
            """
            SELECT a.id, a.device_id, a.level, a.started_at_utc, a.last_fired_at_utc, a.message,
                   d.ip, d.name
            FROM alerts a
            JOIN devices d ON d.id = a.device_id
            WHERE a.acked_at_utc IS NULL AND a.resolved_at_utc IS NULL
            ORDER BY a.last_fired_at_utc DESC, a.id DESC;
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def fire_or_update(self, device_id: int, level: str, started_at_utc: str, message: str) -> int:
        """
        One active row per device+level+episode(started_at).
        If exists -> update last_fired_at; else insert.
        """
        conn = self.db.connect()
        row = conn.execute(
            """
            SELECT id FROM alerts
            WHERE device_id=? AND level=? AND started_at_utc=? AND acked_at_utc IS NULL AND resolved_at_utc IS NULL;
            """,
            (device_id, level, started_at_utc),
        ).fetchone()

        now = utc_now_iso()
        if row:
            aid = int(row["id"])
            conn.execute("UPDATE alerts SET last_fired_at_utc=? WHERE id=?;", (now, aid))
            return aid

        conn.execute(
            """
            INSERT INTO alerts(device_id, level, started_at_utc, last_fired_at_utc, acked_at_utc, resolved_at_utc, message)
            VALUES (?,?,?,?,NULL,NULL,?);
            """,
            (device_id, level, started_at_utc, now, message),
        )
        return int(conn.execute("SELECT last_insert_rowid() AS id;").fetchone()["id"])

    def ack(self, alert_id: int) -> None:
        self.db.connect().execute("UPDATE alerts SET acked_at_utc=? WHERE id=?;", (utc_now_iso(), alert_id))

    def resolve_device_alerts(self, device_id: int) -> None:
        self.db.connect().execute(
            "UPDATE alerts SET resolved_at_utc=? WHERE device_id=? AND resolved_at_utc IS NULL;",
            (utc_now_iso(), device_id),
        )

    def resolve_level(self, device_id: int, level: str) -> None:
        self.db.connect().execute(
            "UPDATE alerts SET resolved_at_utc=? WHERE device_id=? AND level=? AND resolved_at_utc IS NULL;",
            (utc_now_iso(), device_id, level),
        )
