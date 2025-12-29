from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog, QPushButton

from klimozawr.config import AppPaths
from klimozawr.core.models import Device, TickResult
from klimozawr.core.monitor_engine import MonitorEngine
from klimozawr.services.rotation import run_daily_rotation, RotationConfig
from klimozawr.services.sound import SoundManager
from klimozawr.storage.db import SQLiteDatabase
from klimozawr.storage.repositories import UserRepo, DeviceRepo, TelemetryRepo, AlertRepo
from klimozawr.ui.resources import resource_path
from klimozawr.ui.dialogs.create_first_admin import CreateFirstAdminDialog
from klimozawr.ui.dialogs.login import LoginDialog
from klimozawr.ui.dialogs.device_editor import DeviceEditorDialog
from klimozawr.ui.dialogs.user_editor import CreateUserDialog, SetPasswordDialog
from klimozawr.ui.windows.user_main import UserMainWindow
from klimozawr.ui.windows.admin_main import AdminMainWindow

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

        self.session: Session | None = None
        self._selected_device_id: int | None = None

        self._engine = MonitorEngine(max_workers=8)
        self._engine.on_tick = self._enqueue_tick
        self._engine.on_alert = self._enqueue_alert

        yellow_wav = resource_path("resources/sounds/yellow.wav")
        red_wav = resource_path("resources/sounds/red.wav")
        self._sound = SoundManager(yellow_wav=yellow_wav, red_wav=red_wav)

        self._user_win: UserMainWindow | None = None
        self._admin_win: AdminMainWindow | None = None
        self._sound_book: dict[tuple[int, str], str] = {}

        # snapshots for UI cards
        self._snapshots: dict[int, dict] = {}

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
            QMessageBox.critical(None, "Ошибка", f"Не удалось открыть окно: {e}")

    def _show_user(self) -> None:
        self._close_windows()
        self._reload_devices()

        win = UserMainWindow()
        self._user_win = win

        self._wire_common_window(win)
        self._reload_devices()
        win.cards.set_devices(self._snapshots_list())

        win.showFullScreen()

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
            self._admin_win.close()
            self._admin_win = None
        if self._user_win:
            self._user_win.close()
            self._user_win = None

    def _disconnect_ui_signals(self) -> None:
        # Qt: если не отключать, сигналы будут стрелять в мёртвые окна после логаута
        for sig in (getattr(self, "device_updated", None),
                    getattr(self, "alert_fired", None),
                    getattr(self, "alert_cleared", None),
                    getattr(self, "alerts_changed", None)):
            if sig is None:
                continue
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                # уже не было подключений или объект-реципиент уничтожен
                pass

    def _wire_common_window(self, win) -> None:
        # меню
        if hasattr(win, "action_logout"):
            try:
                win.action_logout.triggered.disconnect()
            except Exception:
                pass
            win.action_logout.setEnabled(True)
            win.action_logout.triggered.connect(self.logout)

        if hasattr(win, "action_exit"):
            try:
                win.action_exit.triggered.disconnect()
            except Exception:
                pass
            win.action_exit.setEnabled(True)
            win.action_exit.triggered.connect(self.exit_app)

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

    def _wire_admin_window(self, win: AdminMainWindow) -> None:
        # --- inject Refresh button into admin UI (without touching admin_main.py) ---
        if not hasattr(win, "btn_refresh"):
            win.btn_refresh = QPushButton("Обновить")
            host = getattr(win, "btn_dev_export", None)  # рядом с экспортом устройств
            parent = host.parentWidget() if host is not None else None
            lay = parent.layout() if parent is not None else None
            if lay is not None:
                lay.addWidget(win.btn_refresh)

        try:
            win.btn_refresh.clicked.disconnect()
        except Exception:
            pass
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
        # allow close and quit
        if self._user_win:
            self._user_win.allow_close(True)
        if self._admin_win:
            self._admin_win.allow_close(True)
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
                    "ip": d.ip,
                    "name": d.name,
                    "comment": d.comment,
                    "location": d.location,
                    "owner": d.owner,
                    "yellow_to_red_secs": d.yellow_to_red_secs,
                    "yellow_notify_after_secs": d.yellow_notify_after_secs,
                    "ping_timeout_ms": d.ping_timeout_ms,
                    "status": "YELLOW",
                    "unstable": False,
                    "loss_pct": 100,
                    "rtt_last_ms": None,
                }
            else:
                # refresh metadata
                s = self._snapshots[d.id]
                s.update({
                    "ip": d.ip,
                    "name": d.name,
                    "comment": d.comment,
                    "location": d.location,
                    "owner": d.owner,
                    "yellow_to_red_secs": d.yellow_to_red_secs,
                    "yellow_notify_after_secs": d.yellow_notify_after_secs,
                    "ping_timeout_ms": d.ping_timeout_ms,
                })

        # drop removed
        known = {d.id for d in devs}
        for did in list(self._snapshots.keys()):
            if did not in known:
                self._snapshots.pop(did, None)

    def _snapshots_list(self) -> list[dict]:
        return [self._snapshots[k] for k in sorted(self._snapshots.keys())]

    # --- engine callbacks ---
    def _enqueue_tick(self, tr: TickResult) -> None:
        self.tick_received.emit(tr)

    def _enqueue_alert(self, device_id: int, level: str) -> None:
        self.alert_received.emit(int(device_id), str(level).upper())

    def _on_tick_from_engine(self, tr: TickResult) -> None:
        # store raw tick
        self.telemetry.insert_tick(tr)

        st = self._engine.get_state(tr.device_id)

        # --- status for UI (RED is time-based in state, not always in tr.status) ---
        effective_status = str(getattr(st, "current_status", tr.status)).upper()

        # if device has crossed red threshold in engine state, show RED in UI
        if st and effective_status != "GREEN" and getattr(st, "red_start_utc", None):
            effective_status = "RED"

        # transition events + alert resolution logic
        if st and st.current_status:
            snap = self._snapshots.get(tr.device_id)
            prev = snap.get("status") if snap else None

            if prev and prev != effective_status:
                self.telemetry.insert_event(
                    tr.ts_utc, tr.device_id, "status_transition", f"{prev}->{effective_status}"
                )

            # resolve alerts when green
            if effective_status == "GREEN":
                self.alerts.resolve_device_alerts(tr.device_id)
            # if we're not RED anymore, ensure RED alerts are not hanging
            elif effective_status == "YELLOW":
                self.alerts.resolve_level(tr.device_id, "RED")

            if effective_status == "GREEN":
                self._sound_book.pop((int(tr.device_id), "YELLOW"), None)
                self._sound_book.pop((int(tr.device_id), "RED"), None)
            elif effective_status == "YELLOW":
                self._sound_book.pop((int(tr.device_id), "RED"), None)

        # update snapshot for UI
        if tr.device_id in self._snapshots:
            s = self._snapshots[tr.device_id]
            s["status"] = effective_status
            s["unstable"] = tr.unstable
            s["loss_pct"] = tr.loss_pct
            s["rtt_last_ms"] = tr.rtt_last_ms

        # minute aggregation (simple in-app, best-effort)
        self._aggregate_minute(tr)

        self.device_updated.emit(tr.device_id)

        # if selected device: refresh chart lazily (not every tick)
        if self._selected_device_id == tr.device_id:
            win = self._admin_win or self._user_win
            details = getattr(win, "details", None)
            if details and hasattr(details, "current_period_key"):
                self._refresh_chart(details.current_period_key)

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
            msg = f"YELLOW: 100% потерь ≥ {notify_after} сек"
        else:
            started = (st.red_start_utc or st.first_seen_utc).isoformat()
            to_red = int(snap.get("yellow_to_red_secs", 120))
            msg = f"RED: недоступно > {to_red} сек"

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

        # детали есть только в админ-окне (и в старом user-окне)
        win = self._admin_win or self._user_win
        if win is None:
            return

        if not hasattr(win, "details"):
            return

        snap = self._snapshots.get(int(device_id))
        if snap:
            win.details.set_device(snap)
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
                points.append((ts, r.get("avg_rtt_ms"), r.get("loss_avg")))
        else:
            rows = self.telemetry.select_raw_range(did, since)
            for r in rows:
                ts = datetime.fromisoformat(r["ts_utc"])
                points.append((ts, r.get("rtt_avg_ms"), float(r.get("loss_pct", 0))))

        if self._user_win:
            self._user_win.details.chart.set_data(points)
        if self._admin_win:
            self._admin_win.details.chart.set_data(points)

    # --- admin actions ---
    def _refresh_admin_lists(self) -> None:
        if not self._admin_win:
            return

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        self._admin_win.devices_list.clear()
        for d in self.devices.list_devices():
            it = QListWidgetItem(f"{d.ip}  |  {d.name}")
            it.setData(Qt.UserRole, int(d.id))
            self._admin_win.devices_list.addItem(it)

        self._admin_win.users_list.clear()
        for u in self.users.list_users():
            it = QListWidgetItem(f"{u['username']}  ({u['role']})")
            it.setData(Qt.UserRole, str(u["username"]))
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
                QMessageBox.information(self._admin_win, "Устройства", "Отменено (диалог вернул Cancel).")
                return

            payload = dlg.payload()
            logger.info("UI: device payload=%r", payload)

            action, did = self.devices.upsert_device(payload, is_update_event=True)
            logger.info("DB: upsert_device action=%s id=%s ip=%s", action, did, payload.get("ip"))

            self._reload_devices()
            self._refresh_admin_lists()
            self._refresh_cards_everywhere()

            QMessageBox.information(self._admin_win, "Готово", f"Устройство сохранено ({action}).")
        except Exception as e:
            logger.exception("admin_add_device failed")
            QMessageBox.critical(self._admin_win, "Ошибка", f"{type(e).__name__}: {e}")

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

        self.devices.upsert_device(dlg.payload(), is_update_event=True)
        self._reload_devices()
        self._admin_win.cards.set_devices(self._snapshots_list())
        self._refresh_admin_lists()

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
        path, _ = QFileDialog.getSaveFileName(self._admin_win, "Export devices", "devices.csv", "CSV (*.csv)")
        if not path:
            return
        from pathlib import Path
        self.devices.export_devices_csv(Path(path))
        QMessageBox.information(self._admin_win, "Export", "Export completed.")

    def admin_import_devices_csv(self) -> None:
        if not self._admin_win:
            return
        path, _ = QFileDialog.getOpenFileName(self._admin_win, "Import devices", "", "CSV (*.csv)")
        if not path:
            return
        from pathlib import Path
        rep = self.devices.import_devices_csv(Path(path), max_devices=20)
        msg = f"added={rep.added}, updated={rep.updated}, skipped={rep.skipped}"
        if rep.reasons:
            msg += "\n\n" + "\n".join(rep.reasons[:30])
        QMessageBox.information(self._admin_win, "Import report", msg)

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
            QMessageBox.information(self._admin_win, "Готово", "Пользователь создан.")
        except Exception as e:
            logger.exception("admin_create_user failed")
            QMessageBox.critical(self._admin_win, "Ошибка", f"{type(e).__name__}: {e}")

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
            QMessageBox.warning(self._admin_win, "Users", "You cannot delete your own account while logged in.")
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
            QMessageBox.warning(self._admin_win, "Пользователи", "Выбери пользователя в списке.")
            return

        uid = int(item.data(Qt.UserRole))
        username = item.text().split("  (", 1)[0].strip()

        dlg = SetPasswordDialog(username=username, parent=self._admin_win)
        if dlg.exec() != QDialog.Accepted:
            return

        try:
            self.users.set_password(user_id=uid, new_password=dlg.password())
            logger.info("DB: password changed user_id=%s", uid)
            QMessageBox.information(self._admin_win, "Готово", "Пароль изменён.")
        except Exception as e:
            logger.exception("admin_set_user_password failed")
            QMessageBox.critical(self._admin_win, "Ошибка", f"{type(e).__name__}: {e}")

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
    def _aggregate_minute(self, tr: TickResult) -> None:
        minute = tr.ts_utc.replace(second=0, microsecond=0)
        if self._current_minute is None:
            self._current_minute = minute

        if minute != self._current_minute:
            # flush previous minute
            self._flush_minute(self._current_minute)
            self._minute_bucket.clear()
            self._current_minute = minute

        b = self._minute_bucket.setdefault(tr.device_id, {"ok_ticks": 0, "ticks": 0, "rtts": [], "losses": []})
        b["ticks"] += 1
        if tr.loss_pct < 100:
            b["ok_ticks"] += 1
        if tr.rtt_avg_ms is not None:
            b["rtts"].append(tr.rtt_avg_ms)
        b["losses"].append(tr.loss_pct)

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
