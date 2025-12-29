# klimozawr

Windows 10/11 desktop app (Python 3.12 + PySide6) for monitoring up to 20 IP devices via ICMP (Windows ICMP API through `ctypes`), fully offline except pings.

## Features
- Fullscreen app, no tray.
- App cannot be closed by X / Alt+F4. Exit only via menu: **File → Exit**.
- File → Logout returns to Login without stopping monitor engine.
- Roles: `admin` and `user`.
- First run: if users table empty → create first admin.
- ICMP monitoring:
  - Tick every 1 second per device
  - 3 echo requests per tick
  - `loss_pct` = 0/33/66/100
  - `rtt_last` and `rtt_avg_tick` (only successful replies)
- Status:
  - GREEN: at least 1/3 success
  - YELLOW: 100% loss but downtime <= yellow_to_red_secs
  - RED: 100% loss and downtime > yellow_to_red_secs
  - UNSTABLE: 33% or 66% loss, color stays GREEN but badge shown
- Alerts (in-app + sound):
  - YELLOW sustained >= yellow_notify_after_secs → alert, repeats every 2 min until ACK or status changes
  - RED → immediate alert, repeats every 5 min until ACK or status changes
  - No “recovered” notifications
- History:
  - raw_tick: 72 hours
  - agg_minute: 90 days
  - events: transitions, alert fired/ack, device updated, etc.
  - Daily rotation: prune raw_tick, export old agg_minute/events to CSV and delete them from DB
- CSV devices import/export: UTF-8 with BOM, key = `ip`, updates existing.

## Local data location
Database/logs/exports live under:
`%LOCALAPPDATA%\klimozawr\`
- `data\klimozawr.db`
- `logs\klimozawr.log`
- `exports\YYYY-MM\agg_minute.csv`
- `exports\YYYY-MM\events.csv`

## Setup (dev)
1) Install Python 3.12 (Windows x64).
2) In PowerShell (in project root):
```powershell
.\dev_setup.ps1
