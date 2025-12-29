from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import platform
import shutil
import subprocess
import threading

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog, QPushButton

from klimozawr.config import AppPaths
from klimozawr.core.models import Device, TickResult
from klimozawr.core.monitor_engine import MonitorEngine
from klimozawr.services.rotation import run_daily_rotation, RotationConfig
from klimozawr.services.sound import SoundManager
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.repositories import UserRepo, DeviceRepo, TelemetryRepo, AlertRepo, SettingsRepo
from klimozawr.ui.resources import resource_path
from klimozawr.ui.dialogs.create_first_admin import CreateFirstAdminDialog
from klimozawr.ui.dialogs.login import LoginDialog
from klimozawr.ui.dialogs.device_editor import DeviceEditorDialog
from klimozawr.ui.dialogs.user_editor import CreateUserDialog, SetPasswordDialog
from klimozawr.ui.dialogs.settings_dialog import SettingsDialog
from klimozawr.ui.dialogs.traceroute_dialog import TracerouteDialog
from klimozawr.ui.windows.user_main import UserMainWindow
from klimozawr.ui.windows.admin_main import AdminMainWindow
from klimozawr.ui.strings import role_display, status_display, tr as _t

logger = logging.getLogger("klimozawr.controller")


@dataclass
class Session:
    user_id: int
    username: str
    role: str  # admin/user


class AppController(QObject):
    device_updated = Signal(int)  # device_id
    alerts_changed = Signal()
    alert_fired = Signal(dict)  # payload for AlertsPanel
    alert_cleared = Signal(int)  # alert_id
    tick_received = Signal(object)
    alert_received = Signal(int, str)

    def _refresh_cards_everywhere(self) -> None:
        snaps = self._snapshots_list()
        if self._user_win:
            self._user_win.cards.set_devices(snaps)
        if self._admin_win:
            self._admin_win.cards.set_devices(snaps)

    def admin_refresh(self) -> None:
        """Подтянуть устройства/пользователей и перерисовать UI (без перезапуска)."""
        try:
            self._reload_devices()
            self._refresh_cards_everywhere()
            self._refresh_admin_lists()
        except Exception:
            logger.exception("admin_refresh failed")

    def __init__(self, db: SQLiteDatabase, paths: AppPaths) -> None:
        super().__init__()
        self.db = db
        self.paths = paths

        self.users = UserRepo(db)
        self.devices = DeviceRepo(db)
        self.telemetry = TelemetryRepo(db)
        self.alerts = AlertRepo(db)
        self.settings = SettingsRepo(db)

        self.session: Session | None = None
        self._selected_device_id: int | None = None

        self._engine = MonitorEngine(max_workers=8)
        self._engine.on_tick = self._enqueue_tick
        self._engine.on_alert = self._enqueue_alert
        self._engine.on_resolve = self._enqueue_resolve

        yellow_wav = resource_path("resources/sounds/yellow.wav")
        red_wav = resource_path("resources/sounds/red.wav")
        self._sound = SoundManager(yellow_wav=yellow_wav, red_wav=red_wav)

        self._user_win: UserMainWindow | None = None
        self._admin_win: AdminMainWindow | None = None
        self._sound_book: dict[tuple[int, str], str] = {}

        # snapshots for UI cards
        self._snapshots: dict[int, dict] = {}
        self._raw_logs: dict[int, list[str]] = {}
        self._raw_log_limit = 10

        self._global_sounds = {
            "down": self.settings.get("sound_down_path", ""),
            "up": self.settings.get("sound_up_path", ""),
        }

        # minute aggregation buffers
        self._minute_bucket: dict[int, dict] = {}
        self._current_minute: datetime | None = None

        # daily rotation timer (checks hourly)
        self._last_rotation_date = None
        self._rotation_timer = QTimer()
        self._rotation_timer.setInterval(60 * 60 * 1000)
        self._rotation_timer.timeout.connect(self._maybe_rotate)
        self.tick_received.connect(self._on_tick_from_engine)
        self.alert_received.connect(self._on_alert_from_engine)

        self._chart_timer = QTimer()
        self._chart_timer.setInterval(10 * 1000)
        self._chart_timer.timeout.connect(self._refresh_selected_chart)

    def start(self) -> None:
        # first-run admin
        if self.users.count_users() == 0:
            dlg = CreateFirstAdminDialog(self.users)
            dlg.exec()

        # preload devices snapshots
        self._reload_devices()

        # start engine (keeps running even after logout)
        self._engine.start()
        self._rotation_timer.start()
        self._chart_timer.start()
        self._maybe_rotate()

        self._show_login()

    def _show_login(self) -> None:
        dlg = LoginDialog(self.users)
        dlg.logged_in.connect(self._on_login)
        dlg.exec()

    def _on_login(self, user: dict) -> None:
        try:
            role = str(user.get("role", "")).lower()
            if role == "admin":
                self._show_admin()
            else:
                self._show_user()
        except Exception as e:
            logger.exception("login flow failed")
            QMessageBox.critical(None, _t("dialog.window_open_error_title"), _t("dialog.window_open_error_message", error=e))

    def _show_user(self) -> None:
        self._close_windows()
        self._reload_devices()

        win = UserMainWindow()
        self._user_win = win

        self._wire_common_window(win)
        self._reload_devices()
        win.cards.set_devices(self._snapshots_list())

        win.showMaximized()

    def _show_admin(self) -> None:
        self._close_windows()
        self._reload_devices()

        win = AdminMainWindow()
        self._admin_win = win

        self._wire_common_window(win)
        self._wire_admin_window(win)

        win.cards.set_devices(self._snapshots_list())
        self._refresh_admin_lists()

        win.showFullScreen()

    def _close_windows(self) -> None:
        self._disconnect_ui_signals()

        if self._admin_win:
            self._dispose_window(self._admin_win)
            self._admin_win = None
        if self._user_win:
            self._dispose_window(self._user_win)
            self._user_win = None

    def _dispose_window(self, win, *, hide: bool = True) -> None:
        if hide:
            win.hide()
        win.request_programmatic_close()
        win.deleteLater()

    def _disconnect_ui_signals(self) -> None:
        # Qt: если не отключать, сигналы будут стрелять в мёртвые окна после логаута
        for sig in (getattr(self, "device_updated", None),
                    getattr(self, "alert_fired", None),
                    getattr(self, "alert_cleared", None),
                    getattr(self, "alerts_changed", None)):
            if sig is None:
                continue
            self._safe_disconnect(self, sig)

    @staticmethod
    def _safe_disconnect(owner: QObject, signal) -> None:
        try:
            if owner.receivers(signal) > 0:
                signal.disconnect()
        except (TypeError, RuntimeError):
            # уже не было подключений или объект-реципиент уничтожен
            pass

    def _wire_common_window(self, win) -> None:
        # меню
        if hasattr(win, "action_logout"):
            self._safe_disconnect(win.action_logout, win.action_logout.triggered)
            win.action_logout.setEnabled(True)
            win.action_logout.triggered.connect(self.logout)

        if hasattr(win, "action_exit"):
            self._safe_disconnect(win.action_exit, win.action_exit.triggered)
            win.action_exit.setEnabled(True)
            win.action_exit.triggered.connect(self.exit_app)
        if hasattr(win, "action_export_logs"):
            self._safe_disconnect(win.action_export_logs, win.action_export_logs.triggered)
            win.action_export_logs.setEnabled(True)
            win.action_export_logs.triggered.connect(self.export_all_logs)
        if hasattr(win, "action_settings"):
            self._safe_disconnect(win.action_settings, win.action_settings.triggered)
            win.action_settings.setEnabled(True)
            win.action_settings.triggered.connect(self.open_settings)

        # обновления карточек
        self.device_updated.connect(
            lambda did: win.cards.update_device(self._snapshots[did]) if did in self._snapshots else None
        )

        # если окно содержит детали/алерты (только админ и старый user-режим)
        if hasattr(win, "details") and hasattr(win, "alerts"):
            win.details.period_changed.connect(self._refresh_chart)
            win.cards.device_selected.connect(self._select_device)

            win.alerts.ack_requested.connect(self.ack_alert)
            self.alert_fired.connect(win.alerts.add_alert)
            self.alert_cleared.connect(win.alerts.remove_alert)
        elif hasattr(win, "details"):
            win.details.period_changed.connect(self._refresh_chart)
            win.cards.device_selected.connect(self._select_device)

        if hasattr(win, "details"):
            win.details.traceroute_requested.connect(self.run_traceroute_selected)
            win.details.export_selected_requested.connect(self.export_selected_logs)
            win.details.export_all_requested.connect(self.export_all_logs)

    def _wire_admin_window(self, win: AdminMainWindow) -> None:
        # --- inject Refresh button into admin UI (without touching admin_main.py) ---
        if not hasattr(win, "btn_refresh"):
            win.btn_refresh = QPushButton(_t("admin.button.refresh"))
            host = getattr(win, "btn_dev_export", None)  # рядом с экспортом устройств
            parent = host.parentWidget() if host is not None else None
            lay = parent.layout() if parent is not None else None
            if lay is not None:
                lay.addWidget(win.btn_refresh)

        self._safe_disconnect(win.btn_refresh, win.btn_refresh.clicked)
        win.btn_refresh.clicked.connect(self.admin_refresh)
        win.btn_dev_add.clicked.connect(self.admin_add_device)
        win.btn_dev_edit.clicked.connect(self.admin_edit_device)
        win.btn_dev_del.clicked.connect(self.admin_delete_device)
        win.btn_dev_import.clicked.connect(self.admin_import_devices_csv)
        win.btn_dev_export.clicked.connect(self.admin_export_devices_csv)

        win.btn_usr_add.clicked.connect(self.admin_create_user)
        win.btn_usr_del.clicked.connect(self.admin_delete_user)
        win.btn_usr_pass.clicked.connect(self.admin_set_user_password)
        win.btn_usr_role.clicked.connect(self.admin_toggle_user_role)

    def logout(self) -> None:
        self.session = None
        self._close_windows()
        self._show_login()

    def exit_app(self) -> None:
        self._disconnect_ui_signals()
        if self._user_win:
            self._dispose_window(self._user_win, hide=False)
            self._user_win = None
        if self._admin_win:
            self._dispose_window(self._admin_win, hide=False)
            self._admin_win = None
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    # --- devices snapshots ---
    def _reload_devices(self) -> None:
        devs = self.devices.list_devices()
        self._engine.set_devices(devs)

        # keep snapshots
        for d in devs:
            if d.id not in self._snapshots:
                self._snapshots[d.id] = {
                    "id": d.id,
                    "target": d.target,
                    "resolved_ip": d.resolved_ip,
                    "resolved_at": d.resolved_at,
                    "name": d.name,
                    "comment": d.comment,
                    "location": d.location,
                    "owner": d.owner,
                    "yellow_to_red_secs": d.yellow_to_red_secs,
                    "yellow_notify_after_secs": d.yellow_notify_after_secs,
                    "ping_timeout_ms": d.ping_timeout_ms,
                    "icon_path": d.icon_path,
                    "icon_scale": d.icon_scale,
                    "sound_down_path": d.sound_down_path,
                    "sound_up_path": d.sound_up_path,
                    "status": "YELLOW",
                    "unstable": False,
                    "loss_pct": 100,
                    "rtt_last_ms": None,
                    "last_tick_utc": None,
                }
            else:
                # refresh metadata
                s = self._snapshots[d.id]
                s.update({
                    "target": d.target,
                    "resolved_ip": d.resolved_ip,
                    "resolved_at": d.resolved_at,
                    "name": d.name,
                    "comment": d.comment,
                    "location": d.location,
                    "owner": d.owner,
                    "yellow_to_red_secs": d.yellow_to_red_secs,
                    "yellow_notify_after_secs": d.yellow_notify_after_secs,
                    "ping_timeout_ms": d.ping_timeout_ms,
                    "icon_path": d.icon_path,
                    "icon_scale": d.icon_scale,
                    "sound_down_path": d.sound_down_path,
                    "sound_up_path": d.sound_up_path,
                })

        # drop removed
        known = {d.id for d in devs}
        for did in list(self._snapshots.keys()):
            if did not in known:
                self._snapshots.pop(did, None)

    def _snapshots_list(self) -> list[dict]:
        return [self._snapshots[k] for k in sorted(self._snapshots.keys())]

    # --- engine callbacks ---
    def _enqueue_tick(self, tick: TickResult) -> None:
        self.tick_received.emit(tick)

    def _enqueue_alert(self, device_id: int, level: str) -> None:
        self.alert_received.emit(int(device_id), str(level).upper())

    def _enqueue_resolve(self, device_id: int, resolved_ip: str | None, resolved_at: datetime | None) -> None:
        def _update() -> None:
            try:
                self.devices.update_resolution(int(device_id), resolved_ip, resolved_at)
                snap = self._snapshots.get(int(device_id))
                if snap is not None:
                    snap["resolved_ip"] = resolved_ip
                    snap["resolved_at"] = resolved_at
                logger.info(
                    "dns resolved device=%s target=%s ip=%s at=%s",
                    device_id,
                    snap.get("target") if snap else None,
                    resolved_ip,
                    resolved_at.isoformat() if resolved_at else None,
                )
                if self._selected_device_id == int(device_id):
                    self._update_details_panel(int(device_id))
            except Exception:
                logger.exception("failed to persist resolved ip device=%s ip=%s", device_id, resolved_ip)

        QTimer.singleShot(0, _update)

    def _on_tick_from_engine(self, tick: TickResult) -> None:
        # store raw tick
        self.telemetry.insert_tick(tick)

        st = self._engine.get_state(tick.device_id)

        # --- status for UI (RED is time-based in state, not always in tr.status) ---
        effective_status = str(getattr(st, "current_status", tick.status)).upper()

        # if device has crossed red threshold in engine state, show RED in UI
        if st and effective_status != "GREEN" and getattr(st, "red_start_utc", None):
            effective_status = "RED"

        # transition events + alert resolution logic
        if st and st.current_status:
            snap = self._snapshots.get(tick.device_id)
            prev = snap.get("status") if snap else None

            if prev and prev != effective_status:
                self.telemetry.insert_event(
                    tick.ts_utc, tick.device_id, "status_transition", f"{prev}->{effective_status}"
                )
                self._play_status_sound(tick.device_id, effective_status)

            # resolve alerts when green
            if effective_status == "GREEN":
                self.alerts.resolve_device_alerts(tick.device_id)
            # if we're not RED anymore, ensure RED alerts are not hanging
            elif effective_status == "YELLOW":
                self.alerts.resolve_level(tick.device_id, "RED")

            if effective_status == "GREEN":
                self._sound_book.pop((int(tick.device_id), "YELLOW"), None)
                self._sound_book.pop((int(tick.device_id), "RED"), None)
            elif effective_status == "YELLOW":
                self._sound_book.pop((int(tick.device_id), "RED"), None)

        # update snapshot for UI
        if tick.device_id in self._snapshots:
            s = self._snapshots[tick.device_id]
            s["status"] = effective_status
            s["unstable"] = tick.unstable
            s["loss_pct"] = tick.loss_pct
            s["rtt_last_ms"] = tick.rtt_last_ms
            s["last_tick_utc"] = tick.ts_utc

        self._append_raw_log(
            tick.device_id,
            _t(
                "raw.status_line",
                time=self._format_time_local(tick.ts_utc),
                status=status_display(effective_status),
                loss=tick.loss_pct,
                rtt=tick.rtt_last_ms or _t("placeholder.na"),
            ),
        )

        # minute aggregation (simple in-app, best-effort)
        self._aggregate_minute(tick)

        self.device_updated.emit(tick.device_id)

        # if selected device: refresh chart lazily (not every tick)
        if self._selected_device_id == tick.device_id:
            win = self._admin_win or self._user_win
            details = getattr(win, "details", None)
            if details and hasattr(details, "current_period_key"):
                self._refresh_chart(details.current_period_key)
                self._update_details_panel(tick.device_id)

    def _on_alert_from_engine(self, device_id: int, level: str) -> None:
        st = self._engine.get_state(device_id)
        if not st:
            return

        snap = self._snapshots.get(int(device_id))
        if snap is None:
            dev = next((d for d in self.devices.list_devices() if int(d.id) == int(device_id)), None)
            snap = {
                "yellow_to_red_secs": getattr(dev, "yellow_to_red_secs", 120) if dev else 120,
                "yellow_notify_after_secs": getattr(dev, "yellow_notify_after_secs", 30) if dev else 30,
            }

        # decide episode start timestamp
        if level == "YELLOW":
            started = (st.yellow_start_utc or st.first_seen_utc).isoformat()
            notify_after = int(snap.get("yellow_notify_after_secs", 30))
            msg = _t(
                "alerts.message.yellow",
                level=status_display(level),
                seconds=notify_after,
            )
        else:
            started = (st.red_start_utc or st.first_seen_utc).isoformat()
            to_red = int(snap.get("yellow_to_red_secs", 120))
            msg = _t(
                "alerts.message.red",
                level=status_display(level),
                seconds=to_red,
            )

        alert_id = self.alerts.fire_or_update(
            device_id=device_id,
            level=level,
            started_at_utc=started,
            message=msg,
        )
        logger.info(
            "alert fired device=%s level=%s started_at=%s alert_id=%s",
            device_id,
            level,
            started,
            alert_id,
        )
        self.telemetry.insert_event(
            datetime.now(timezone.utc),
            device_id,
            "alert_fired",
            f"{level} alert_id={alert_id}",
        )

        payload = {
            "id": int(alert_id),
            "device_id": int(device_id),
            "level": str(level),
            "started_at_utc": str(started),
            "message": str(msg),
        }

        sound_key = (int(device_id), str(level))
        if self._sound_book.get(sound_key) != started:
            self._sound_book[sound_key] = started
            logger.info("sound play device=%s level=%s started_at=%s", device_id, level, started)
            QTimer.singleShot(0, lambda lvl=level: self._sound.play(lvl))

        # ✅ теперь UI получает событие сразу
        self.alert_fired.emit(payload)
        self.alerts_changed.emit()

    def ack_alert(self, alert_id: int, level: str, device_id: int) -> None:
        self.alerts.ack(alert_id)
        self.telemetry.insert_event(datetime.now(timezone.utc), device_id, "alert_ack", f"{level} alert_id={alert_id}")
        self._engine.ack_device(int(device_id), str(level).upper())
        self.alert_cleared.emit(int(alert_id))
        self.alerts_changed.emit()

    # --- selection/details/chart ---
    def _select_device(self, device_id: int) -> None:
        self._selected_device_id = int(device_id)
        logger.info("UI: device selected id=%s", device_id)

        # детали есть только в админ-окне (и в старом user-окне)
        win = self._admin_win or self._user_win
        if win is None:
            return

        if not hasattr(win, "details"):
            return

        snap = self._snapshots.get(int(device_id))
        if snap:
            self._update_details_panel(device_id)
            # можно обновить график текущего периода
            self._refresh_chart(getattr(win.details, "current_period_key", "1h"))

    def _refresh_chart(self, period_key: str) -> None:
        did = self._selected_device_id
        if not did:
            return

        now = datetime.now(timezone.utc)
        use_agg = period_key in ("7d", "30d", "90d")

        if period_key == "1h":
            since = now - timedelta(hours=1)
        elif period_key == "24h":
            since = now - timedelta(hours=24)
        elif period_key == "72h":
            since = now - timedelta(hours=72)
        elif period_key == "7d":
            since = now - timedelta(days=7)
        elif period_key == "30d":
            since = now - timedelta(days=30)
        else:
            since = now - timedelta(days=90)

        points: list[tuple[datetime, float | None, float | None]] = []
        if use_agg:
            rows = self.telemetry.select_agg_range(did, since)
            for r in rows:
                ts = datetime.fromisoformat(r["minute_ts_utc"])
                ts = self._to_local(ts)
                points.append((ts, r.get("avg_rtt_ms"), r.get("loss_avg")))
        else:
            rows = self.telemetry.select_raw_range(did, since)
            for r in rows:
                ts = datetime.fromisoformat(r["ts_utc"])
                ts = self._to_local(ts)
                points.append((ts, r.get("rtt_avg_ms"), float(r.get("loss_pct", 0))))

        if self._user_win:
            self._user_win.details.chart.set_data(points)
        if self._admin_win:
            self._admin_win.details.chart.set_data(points)

    def _refresh_selected_chart(self) -> None:
        did = self._selected_device_id
        if not did:
            return
        win = self._admin_win or self._user_win
        details = getattr(win, "details", None)
        if details and hasattr(details, "current_period_key"):
            self._refresh_chart(details.current_period_key)
        self._update_details_panel(did)

    def _update_details_panel(self, device_id: int) -> None:
        win = self._admin_win or self._user_win
        if not win or not hasattr(win, "details"):
            return
        snap = self._snapshots.get(int(device_id))
        if not snap:
            win.details.clear()
            return
        status = str(snap.get("status", "UNKNOWN")).upper()
        last_tick = snap.get("last_tick_utc")
        rtt = snap.get("rtt_last_ms")
        loss = snap.get("loss_pct")
        rtt_txt = _t("placeholder.na") if rtt is None else f"{int(rtt)} {_t('unit.ms')}"
        loss_txt = _t("placeholder.na") if loss is None else f"{int(loss)}%"
        last_txt = win.details.format_timestamp(last_tick)
        elapsed_txt = self._format_elapsed(device_id, status)

        raw_lines = self._raw_logs.get(int(device_id), [])
        raw_tail = raw_lines[-self._raw_log_limit :]

        win.details.set_device_details(
            name=str(snap.get("name", "") or ""),
            target=str(snap.get("target", "") or ""),
            resolved_ip=str(snap.get("resolved_ip", "") or ""),
            status=status,
            rtt_ms=rtt_txt,
            loss_pct=loss_txt,
            last_seen=last_txt,
            elapsed=elapsed_txt,
            raw_lines=raw_tail,
        )

    def _format_elapsed(self, device_id: int, status: str) -> str:
        st = self._engine.get_state(device_id)
        if not st:
            return _t("placeholder.na")
        base: datetime | None
        if status == "GREEN":
            base = st.last_ok_utc or st.first_seen_utc
        elif status == "YELLOW":
            base = st.yellow_start_utc or st.first_seen_utc
        elif status == "RED":
            base = st.red_start_utc or st.first_seen_utc
        else:
            return _t("placeholder.na")
        if not base:
            return _t("placeholder.na")
        delta = datetime.now(timezone.utc) - base
        secs = int(delta.total_seconds())
        mins, sec = divmod(secs, 60)
        hrs, min_ = divmod(mins, 60)
        days, hr = divmod(hrs, 24)
        if days > 0:
            return f"{days}{_t('unit.day_short')} {hr}{_t('unit.hour_short')} {min_}{_t('unit.minute_short')}"
        if hrs > 0:
            return f"{hr}{_t('unit.hour_short')} {min_}{_t('unit.minute_short')} {sec}{_t('unit.second_short')}"
        if mins > 0:
            return f"{min_}{_t('unit.minute_short')} {sec}{_t('unit.second_short')}"
        return f"{sec}{_t('unit.second_short')}"

    def _append_raw_log(self, device_id: int, line: str) -> None:
        buf = self._raw_logs.setdefault(int(device_id), [])
        buf.append(str(line))
        if len(buf) > self._raw_log_limit * 3:
            del buf[: len(buf) - self._raw_log_limit * 3]

    def _play_status_sound(self, device_id: int, status: str) -> None:
        snap = self._snapshots.get(int(device_id), {})
        status = status.upper()
        if status == "GREEN":
            path = snap.get("sound_up_path") or self._global_sounds.get("up")
        elif status in {"YELLOW", "RED", "DOWN"}:
            path = snap.get("sound_down_path") or self._global_sounds.get("down")
        else:
            path = None
        if path:
            logger.info("sound play device=%s status=%s path=%s", device_id, status, path)
            self._sound.play_path(str(path))
        else:
            logger.info("sound not configured device=%s status=%s", device_id, status)

    def _to_local(self, ts_utc: datetime | None) -> datetime | None:
        if not ts_utc:
            return None
        # UI показывает локальное время ПК, хранение в UTC.
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=timezone.utc)
        return ts_utc.astimezone()

    def _format_time_local(self, ts_utc: datetime | None) -> str:
        ts_local = self._to_local(ts_utc)
        if not ts_local:
            return _t("placeholder.na")
        return ts_local.strftime("%H:%M:%S")

    # --- admin actions ---
    def run_traceroute_selected(self) -> None:
        did = self._selected_device_id
        if not did:
            QMessageBox.warning(
                self._admin_win or self._user_win,
                _t("dialog.device_select_title"),
                _t("dialog.device_select_message"),
            )
            return
        snap = self._snapshots.get(int(did))
        if not snap:
            QMessageBox.warning(
                self._admin_win or self._user_win,
                _t("dialog.device_select_title"),
                _t("dialog.device_select_message"),
            )
            return
        target = str(snap.get("target", "") or "")
        name = str(snap.get("name", "") or "")
        if not target:
            QMessageBox.warning(
                self._admin_win or self._user_win,
                _t("dialog.window_open_error_title"),
                _t("dialog.window_open_error_message", error="Target is empty"),
            )
            return
        logger.info("UI: traceroute start device_id=%s target=%s", did, target)

        def _worker() -> None:
            cmd = ["tracert", "-d", target] if platform.system().lower() == "windows" else ["traceroute", target]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode != 0:
                    logger.warning("traceroute non-zero exit code=%s target=%s", res.returncode, target)
                output = res.stdout.strip() or res.stderr.strip()
            except Exception as exc:
                logger.exception("traceroute failed target=%s", target)
                output = f"{type(exc).__name__}: {exc}"

            self._append_raw_log(did, _t("raw.traceroute_start", target=target))
            for line in output.splitlines()[:20]:
                self._append_raw_log(did, line)

            def _show() -> None:
                title = _t("traceroute.title", target=name or target)
                dlg = TracerouteDialog(title=title, output=output, parent=self._admin_win or self._user_win)
                dlg.exec()
                self._update_details_panel(did)
                logger.info("UI: traceroute finished device_id=%s target=%s", did, target)

            QTimer.singleShot(0, _show)

        threading.Thread(target=_worker, name="traceroute", daemon=True).start()

    def export_selected_logs(self) -> None:
        did = self._selected_device_id
        if not did:
            return
        snap = self._snapshots.get(int(did))
        label = snap.get("name") or snap.get("target") or f"device_{did}"
        default = self.paths.exports_dir / f"{label}_logs.csv"
        path, _ = QFileDialog.getSaveFileName(
            self._admin_win or self._user_win,
            _t("dialog.export_selected_title"),
            str(default),
            _t("dialog.export_logs_filter"),
        )
        if not path:
            return
        logger.info("UI: export logs selected device=%s path=%s", did, path)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        self.telemetry.export_raw_csv(Path(path), device_id=int(did), since_utc=since)
        QMessageBox.information(
            self._admin_win or self._user_win,
            _t("dialog.export_completed_title"),
            _t("dialog.export_completed_message"),
        )

    def export_all_logs(self) -> None:
        default = self.paths.exports_dir / _t("dialog.export_all_logs_filename")
        path, _ = QFileDialog.getSaveFileName(
            self._admin_win or self._user_win,
            _t("dialog.export_all_title"),
            str(default),
            _t("dialog.export_logs_filter"),
        )
        if not path:
            return
        logger.info("UI: export logs all path=%s", path)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        self.telemetry.export_raw_csv(Path(path), device_id=None, since_utc=since)
        QMessageBox.information(
            self._admin_win or self._user_win,
            _t("dialog.export_completed_title"),
            _t("dialog.export_completed_message"),
        )

    def open_settings(self) -> None:
        initial = {
            "sound_down_path": self.settings.get("sound_down_path", ""),
            "sound_up_path": self.settings.get("sound_up_path", ""),
        }
        dlg = SettingsDialog(initial=initial, parent=self._admin_win)
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        down = self._save_asset(payload.get("sound_down_path", ""), "sounds")
        up = self._save_asset(payload.get("sound_up_path", ""), "sounds")
        self.settings.set("sound_down_path", down)
        self.settings.set("sound_up_path", up)
        self._global_sounds["down"] = down
        self._global_sounds["up"] = up
        logger.info("UI: settings updated global sounds down=%s up=%s", down, up)
        QMessageBox.information(
            self._admin_win,
            _t("dialog.settings_saved_title"),
            _t("dialog.settings_saved_message"),
        )

    def _prepare_device_payload(self, payload: dict) -> dict:
        icon = self._save_asset(payload.get("icon_path", ""), "icons")
        down = self._save_asset(payload.get("sound_down_path", ""), "sounds")
        up = self._save_asset(payload.get("sound_up_path", ""), "sounds")
        new_payload = dict(payload)
        new_payload["icon_path"] = icon
        new_payload["sound_down_path"] = down
        new_payload["sound_up_path"] = up
        logger.info(
            "UI: apply per-host settings icon=%s scale=%s down=%s up=%s",
            icon,
            payload.get("icon_scale", 100),
            down,
            up,
        )
        return new_payload

    def _save_asset(self, path: str, bucket: str) -> str:
        if not path:
            return ""
        src = Path(path)
        if not src.exists():
            return ""
        dest_dir = self.paths.data_dir / "assets" / bucket
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if dest.exists() and dest.resolve() != src.resolve():
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = dest_dir / f"{src.stem}_{stamp}{src.suffix}"
        try:
            if dest.resolve() != src.resolve():
                shutil.copy2(src, dest)
            return str(dest)
        except Exception:
            logger.exception("failed to store asset %s", src)
            return str(src)

    def _refresh_admin_lists(self) -> None:
        if not self._admin_win:
            return

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        self._admin_win.devices_list.clear()
        for d in self.devices.list_devices():
            it = QListWidgetItem(_t("admin.devices_list_item", target=d.target, name=d.name))
            it.setData(Qt.UserRole, int(d.id))
            self._admin_win.devices_list.addItem(it)

        self._admin_win.users_list.clear()
        for u in self.users.list_users():
            it = QListWidgetItem(
                _t(
                    "admin.users_list_item",
                    username=u["username"],
                    role=role_display(u["role"]),
                )
            )
            it.setData(Qt.UserRole, int(u["id"]))
            self._admin_win.users_list.addItem(it)

    def admin_add_device(self) -> None:
        if not self._admin_win:
            return

        import logging
        from PySide6.QtWidgets import QMessageBox

        logger = logging.getLogger(__name__)
        logger.info("UI: admin_add_device clicked")

        try:
            dlg = DeviceEditorDialog(None, parent=self._admin_win)
            res = dlg.exec()
            logger.info("UI: DeviceEditorDialog result=%s", res)

            if res != QDialog.Accepted:
                QMessageBox.information(
                    self._admin_win,
                    _t("dialog.device_cancelled_title"),
                    _t("dialog.device_cancelled_message"),
                )
                return

            payload = self._prepare_device_payload(dlg.payload())
            logger.info("UI: device payload=%r", payload)

            action, did = self.devices.upsert_device(payload, is_update_event=True)
            logger.info("DB: upsert_device action=%s id=%s target=%s", action, did, payload.get("target"))

            self._reload_devices()
            self._refresh_admin_lists()
            self._refresh_cards_everywhere()

            QMessageBox.information(
                self._admin_win,
                _t("dialog.device_saved_title"),
                _t("dialog.device_saved_message", action=action),
            )
        except Exception as e:
            logger.exception("admin_add_device failed")
            QMessageBox.critical(self._admin_win, _t("dialog.window_open_error_title"), f"{type(e).__name__}: {e}")

    def admin_edit_device(self) -> None:
        if not self._admin_win:
            return

        from PySide6.QtCore import Qt
        it = self._admin_win.devices_list.currentItem()
        if not it:
            return

        did = it.data(Qt.UserRole)
        if did is None:
            return
        did = int(did)

        dev = next((d for d in self.devices.list_devices() if int(d.id) == did), None)
        if not dev:
            return

        dlg = DeviceEditorDialog(dev, parent=self._admin_win)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        try:
            payload = self._prepare_device_payload(dlg.payload())
            self.devices.update_device_by_id(dev.id, payload, is_update_event=True)
            self._reload_devices()
            self._admin_win.cards.set_devices(self._snapshots_list())
            self._refresh_admin_lists()
        except Exception as e:
            logger.exception("admin_edit_device failed")
            QMessageBox.critical(self._admin_win, _t("dialog.window_open_error_title"), f"{type(e).__name__}: {e}")

    def admin_delete_device(self) -> None:
        if not self._admin_win:
            return
        it = self._admin_win.devices_list.currentItem()
        if not it:
            return
        from PySide6.QtCore import Qt
        did = int(it.data(Qt.UserRole))
        self.devices.delete_device(did)
        self._reload_devices()
        self._refresh_admin_lists()
        self._admin_win.cards.set_devices(self._snapshots_list())

    def admin_export_devices_csv(self) -> None:
        if not self._admin_win:
            return
        path, _ = QFileDialog.getSaveFileName(
            self._admin_win,
            _t("dialog.export_devices_title"),
            _t("dialog.export_devices_filename"),
            _t("dialog.csv_filter"),
        )
        if not path:
            return
        from pathlib import Path
        self.devices.export_devices_csv(Path(path))
        QMessageBox.information(
            self._admin_win,
            _t("dialog.export_devices_title"),
            _t("dialog.export_devices_message"),
        )

    def admin_import_devices_csv(self) -> None:
        if not self._admin_win:
            return
        path, _ = QFileDialog.getOpenFileName(
            self._admin_win,
            _t("dialog.import_devices_title"),
            "",
            _t("dialog.csv_filter"),
        )
        if not path:
            return
        from pathlib import Path
        rep = self.devices.import_devices_csv(Path(path), max_devices=20)
        msg = _t(
            "dialog.import_report_summary",
            added=rep.added,
            updated=rep.updated,
            skipped=rep.skipped,
        )
        if rep.reasons:
            msg += "\n\n" + _t("dialog.import_report_reasons_header") + "\n" + "\n".join(rep.reasons[:30])
        QMessageBox.information(self._admin_win, _t("dialog.import_report_title"), msg)

        self._reload_devices()
        self._refresh_admin_lists()
        self._admin_win.cards.set_devices(self._snapshots_list())

    def admin_create_user(self) -> None:
        if not self._admin_win:
            return

        import logging
        from PySide6.QtWidgets import QMessageBox, QDialog
        from klimozawr.ui.dialogs.user_editor import CreateUserDialog

        logger = logging.getLogger(__name__)
        logger.info("UI: admin_create_user clicked")

        dlg = CreateUserDialog(parent=self._admin_win)
        if dlg.exec() != QDialog.Accepted:
            return

        p = dlg.payload()
        try:
            # ожидаем, что репозиторий умеет это делать
            uid = self.users.create_user(username=p.username, password=p.password, role=p.role)
            logger.info("DB: user created id=%s username=%s role=%s", uid, p.username, p.role)
            self._refresh_admin_lists()
            QMessageBox.information(
                self._admin_win,
                _t("dialog.user_created_title"),
                _t("dialog.user_created_message"),
            )
        except Exception as e:
            logger.exception("admin_create_user failed")
            QMessageBox.critical(self._admin_win, _t("dialog.window_open_error_title"), f"{type(e).__name__}: {e}")

    def admin_delete_user(self) -> None:
        if not self._admin_win:
            return
        it = self._admin_win.users_list.currentItem()
        if not it:
            return
        from PySide6.QtCore import Qt
        uid = int(it.data(Qt.UserRole))
        # avoid deleting yourself
        if self.session and uid == self.session.user_id:
            QMessageBox.warning(
                self._admin_win,
                _t("dialog.user_delete_self_title"),
                _t("dialog.user_delete_self_message"),
            )
            return
        self.users.delete_user(uid)
        self._refresh_admin_lists()

    def admin_set_user_password(self) -> None:
        if not self._admin_win:
            return

        import logging
        from PySide6.QtWidgets import QMessageBox, QDialog
        from klimozawr.ui.dialogs.user_editor import SetPasswordDialog
        from PySide6.QtCore import Qt

        logger = logging.getLogger(__name__)

        item = self._admin_win.users_list.currentItem()
        if not item:
            QMessageBox.warning(
                self._admin_win,
                _t("dialog.user_select_title"),
                _t("dialog.user_select_message"),
            )
            return

        uid = int(item.data(Qt.UserRole))
        username = item.text().split("(", 1)[0].strip()

        dlg = SetPasswordDialog(username=username, parent=self._admin_win)
        if dlg.exec() != QDialog.Accepted:
            return

        try:
            self.users.set_password(uid, dlg.password())
            logger.info("DB: password changed user_id=%s", uid)
            QMessageBox.information(
                self._admin_win,
                _t("dialog.user_password_changed_title"),
                _t("dialog.user_password_changed_message"),
            )
        except Exception as e:
            logger.exception("admin_set_user_password failed")
            QMessageBox.critical(self._admin_win, _t("dialog.window_open_error_title"), f"{type(e).__name__}: {e}")

    def admin_toggle_user_role(self) -> None:
        if not self._admin_win:
            return
        it = self._admin_win.users_list.currentItem()
        if not it:
            return
        uid = int(it.data(0x0100))
        # fetch role
        users = self.users.list_users()
        u = next((x for x in users if int(x["id"]) == uid), None)
        if not u:
            return
        new_role = "admin" if u["role"] == "user" else "user"
        self.users.update_role(uid, new_role)
        self._refresh_admin_lists()

    # --- minute aggregation (best-effort) ---
    def _aggregate_minute(self, tick: TickResult) -> None:
        minute = tick.ts_utc.replace(second=0, microsecond=0)
        if self._current_minute is None:
            self._current_minute = minute

        if minute != self._current_minute:
            # flush previous minute
            self._flush_minute(self._current_minute)
            self._minute_bucket.clear()
            self._current_minute = minute

        b = self._minute_bucket.setdefault(tick.device_id, {"ok_ticks": 0, "ticks": 0, "rtts": [], "losses": []})
        b["ticks"] += 1
        if tick.loss_pct < 100:
            b["ok_ticks"] += 1
        if tick.rtt_avg_ms is not None:
            b["rtts"].append(tick.rtt_avg_ms)
        b["losses"].append(tick.loss_pct)

    def _flush_minute(self, minute: datetime) -> None:
        for did, b in self._minute_bucket.items():
            ticks = max(1, int(b["ticks"]))
            uptime_ratio = float(b["ok_ticks"]) / float(ticks)
            losses = b["losses"] or [100]
            loss_avg = float(sum(losses)) / float(len(losses))
            rtts = b["rtts"]
            avg_rtt = (float(sum(rtts)) / float(len(rtts))) if rtts else None
            max_rtt = int(max(rtts)) if rtts else None
            self.telemetry.upsert_minute_agg(did, minute, avg_rtt, max_rtt, loss_avg, uptime_ratio)

    # --- rotation ---
    def _maybe_rotate(self) -> None:
        today = datetime.now().date()
        if self._last_rotation_date == today:
            return
        self._last_rotation_date = today
        try:
            run_daily_rotation(self.telemetry, self.paths.exports_dir, RotationConfig())
        except Exception:
            logger.exception("rotation failed")
