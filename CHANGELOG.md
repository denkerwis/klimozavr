# Changelog

## 0.1.0 (2025-12-29)
- Initial scaffolding: PySide6 UI, SQLite storage, ICMP monitoring via Windows API (ctypes).
- Login + roles (admin/user), first-run admin creation.
- Monitor engine 1s tick, 3 echo per tick, statuses GREEN/YELLOW/RED + UNSTABLE.
- Alerts with ACK, repeat timers, in-app notifications + sounds.
- History: raw_tick (72h), agg_minute (90d), events; daily rotation + CSV export.
- Admin: device/user management + CSV import/export for devices.
- PyInstaller build scripts, basic pytest coverage.
