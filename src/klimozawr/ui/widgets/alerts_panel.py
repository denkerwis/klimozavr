from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout
)


class AlertsPanel(QWidget):
    """
    Панель алертов внутри приложения (без трея).
    Принимает события add_alert/remove_alert и даёт ACK через сигнал.
    """
    ack_requested = Signal(int, str, int)  # alert_id, level, device_id

    def __init__(self) -> None:
        super().__init__()

        self._alerts: Dict[int, dict] = {}

        title = QLabel("АЛЕРТЫ")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.list = QListWidget()
        self.list.setAlternatingRowColors(False)

        root = QVBoxLayout()
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(title)
        root.addWidget(self.list, 1)
        self.setLayout(root)

    # --- API для AppController wiring ---

    def set_alerts(self, alerts: List[dict]) -> None:
        """Полная замена списка (на будущее/инициализацию)."""
        self._alerts = {int(a["id"]): dict(a) for a in alerts if "id" in a}
        self._rebuild()

    def add_alert(self, alert: dict) -> None:
        """
        Upsert: если алерт с таким id уже есть, обновляем.
        Ожидаемый формат:
          {id, device_id, level, started_at_utc, message}
        """
        if not alert or "id" not in alert:
            return
        aid = int(alert["id"])
        self._alerts[aid] = dict(alert)
        self._rebuild()

    def remove_alert(self, alert_id: int) -> None:
        self._alerts.pop(int(alert_id), None)
        self._rebuild()

    def clear(self) -> None:
        self._alerts.clear()
        self._rebuild()

    # --- internal ---

    def _rebuild(self) -> None:
        self.list.clear()

        # сортировка: сначала RED, потом YELLOW, потом по времени
        def sort_key(a: dict) -> tuple:
            lvl = str(a.get("level", "")).upper()
            pr = 0 if lvl == "RED" else 1 if lvl == "YELLOW" else 2
            ts = str(a.get("started_at_utc", ""))
            return (pr, ts)

        for a in sorted(self._alerts.values(), key=sort_key):
            aid = int(a.get("id", 0))
            did = int(a.get("device_id", 0))
            lvl = str(a.get("level", "")).upper()
            msg = str(a.get("message", "")).strip()

            item = QListWidgetItem()
            w = QWidget()
            lay = QHBoxLayout()
            lay.setContentsMargins(8, 6, 8, 6)
            lay.setSpacing(10)

            text = QLabel(f"[{lvl}] устройство #{did}: {msg}")
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            btn = QPushButton("Подтвердить")
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda _=False, _aid=aid, _lvl=lvl, _did=did: self.ack_requested.emit(_aid, _lvl, _did))

            lay.addWidget(text, 1)
            lay.addWidget(btn, 0)
            w.setLayout(lay)

            item.setSizeHint(w.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, w)


