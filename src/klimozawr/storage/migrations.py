from __future__ import annotations

import logging
from klimozawr.storage.db import SQLiteDatabase

logger = logging.getLogger("klimozawr.migrations")

SCHEMA_VERSION = 1


def apply_migrations(db: SQLiteDatabase) -> None:
    conn = db.connect()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta ("
        "id INTEGER PRIMARY KEY CHECK (id=1), "
        "version INTEGER NOT NULL"
        ");"
    )
    row = conn.execute("SELECT version FROM schema_meta WHERE id=1;").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_meta(id, version) VALUES (1, 0);")
        row = conn.execute("SELECT version FROM schema_meta WHERE id=1;").fetchone()

    ver = int(row["version"])
    if ver >= SCHEMA_VERSION:
        return

    logger.info("migrating schema from %s to %s", ver, SCHEMA_VERSION)

    if ver < 1:
        _migrate_v1(conn)
        conn.execute("UPDATE schema_meta SET version=? WHERE id=1;", (1,))

    logger.info("migrations done")


def _migrate_v1(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('admin','user')),
          created_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS devices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ip TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          comment TEXT NOT NULL DEFAULT '',
          location TEXT NOT NULL DEFAULT '',
          owner TEXT NOT NULL DEFAULT '',
          yellow_to_red_secs INTEGER NOT NULL DEFAULT 120,
          yellow_notify_after_secs INTEGER NOT NULL DEFAULT 30,
          ping_timeout_ms INTEGER NOT NULL DEFAULT 1000,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_tick (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
          ts_utc TEXT NOT NULL,
          loss_pct INTEGER NOT NULL,
          rtt_last_ms INTEGER NULL,
          rtt_avg_ms INTEGER NULL,
          status TEXT NOT NULL,
          unstable INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_raw_tick_device_ts ON raw_tick(device_id, ts_utc);

        CREATE TABLE IF NOT EXISTS agg_minute (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
          minute_ts_utc TEXT NOT NULL,
          avg_rtt_ms REAL NULL,
          max_rtt_ms INTEGER NULL,
          loss_avg REAL NOT NULL,
          uptime_ratio REAL NOT NULL,
          UNIQUE(device_id, minute_ts_utc)
        );
        CREATE INDEX IF NOT EXISTS idx_agg_minute_device_ts ON agg_minute(device_id, minute_ts_utc);

        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts_utc TEXT NOT NULL,
          device_id INTEGER NULL REFERENCES devices(id) ON DELETE SET NULL,
          kind TEXT NOT NULL,
          detail TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_utc);

        CREATE TABLE IF NOT EXISTS alerts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
          level TEXT NOT NULL CHECK(level IN ('YELLOW','RED')),
          started_at_utc TEXT NOT NULL,
          last_fired_at_utc TEXT NOT NULL,
          acked_at_utc TEXT NULL,
          resolved_at_utc TEXT NULL,
          message TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(device_id, level, acked_at_utc, resolved_at_utc);
        """
    )
