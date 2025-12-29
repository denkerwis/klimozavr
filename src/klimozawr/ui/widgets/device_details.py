from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox

from klimozawr.ui.widgets.charts import RttLossChart


class DeviceDetailsPanel(QWidget):
    period_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self.title = QLabel("Детали устройства")
        self.title.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.period = QComboBox()
        self.period.addItem("1 час", "1h")
        self.period.addItem("24 часа", "24h")
        self.period.addItem("72 часа", "72h")
        self.period.addItem("7 дней", "7d")
        self.period.addItem("30 дней", "30d")
        self.period.addItem("90 дней", "90d")
        self.period.currentIndexChanged.connect(self._on_period)

        self.current_period_key = "1h"

        self.meta = QLabel("")
        self.meta.setStyleSheet("font-size: 12px;")
        self.meta.setWordWrap(True)

        self.chart = RttLossChart()

        root = QVBoxLayout()
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self.title)
        root.addWidget(self.period)
        root.addWidget(self.chart, 1)
        root.addWidget(self.meta)
        self.setLayout(root)

    def _on_period(self) -> None:
        key = str(self.period.currentData())
        self.current_period_key = key
        self.period_changed.emit(key)

    def set_device(self, snapshot: dict | None) -> None:
        if not snapshot:
            self.title.setText("Детали устройства")
            self.meta.setText("")
            return

        ip = str(snapshot.get("ip", "") or "")
        name = str(snapshot.get("name", "") or "")
        self.title.setText(f"{name} ({ip})" if name else ip)

        status = str(snapshot.get("status", "GREEN"))
        unstable = bool(snapshot.get("unstable", False))
        loss = snapshot.get("loss_pct", None)

        rtt = snapshot.get("rtt_last", None)
        if rtt is None:
            rtt = snapshot.get("rtt_last_ms", None)

        rtt_txt = "—"
        if rtt is not None:
            try:
                rtt_txt = f"{int(float(rtt))} мс"
            except Exception:
                rtt_txt = str(rtt)

        loss_txt = "—"
        if loss is not None:
            try:
                loss_txt = f"{int(loss)}%"
            except Exception:
                loss_txt = str(loss)

        owner = str(snapshot.get("owner", "") or "")
        location = str(snapshot.get("location", "") or "")
        comment = str(snapshot.get("comment", "") or "")

        self.meta.setText(
            f"статус: {status}   нестабильно: {'да' if unstable else 'нет'}\n"
            f"потери: {loss_txt}   rtt: {rtt_txt}\n"
            f"владелец: {owner}   локация: {location}\n"
            f"комментарий: {comment}"
        )


