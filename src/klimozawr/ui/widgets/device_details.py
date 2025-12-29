from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QPlainTextEdit,
)

from klimozawr.ui.widgets.charts import RttLossChart


class DeviceDetailsPanel(QWidget):
    period_changed = Signal(str)
    traceroute_requested = Signal()
    export_selected_requested = Signal()
    export_all_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.title = QLabel("Детали устройства")
        self.title.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.host_label = QLabel("—")
        host_font = QFont()
        host_font.setPointSize(13)
        host_font.setBold(True)
        self.host_label.setFont(host_font)
        self.host_label.setWordWrap(True)

        self.status_label = QLabel("Статус: —")
        status_font = QFont()
        status_font.setPointSize(12)
        status_font.setBold(True)
        self.status_label.setFont(status_font)

        self.rtt_label = QLabel("RTT: —")
        self.loss_label = QLabel("Loss: —")
        self.last_label = QLabel("LAST: —")
        self.elapsed_label = QLabel("ELAPSED: —")

        metrics = QGridLayout()
        metrics.addWidget(self.rtt_label, 0, 0)
        metrics.addWidget(self.loss_label, 0, 1)
        metrics.addWidget(self.last_label, 1, 0)
        metrics.addWidget(self.elapsed_label, 1, 1)

        self.raw_label = QLabel("RAW output (последние строки)")
        self.raw_output = QPlainTextEdit()
        self.raw_output.setReadOnly(True)
        self.raw_output.setMaximumBlockCount(20)
        self.raw_output.setMinimumHeight(90)
        self.raw_output.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 11px;")

        self.btn_traceroute = QPushButton("Traceroute (выбранный)")
        self.btn_export = QPushButton("Экспорт логов (выбранный)")
        self.btn_export_all = QPushButton("Экспорт логов (общая)")
        self.btn_traceroute.clicked.connect(self.traceroute_requested.emit)
        self.btn_export.clicked.connect(self.export_selected_requested.emit)
        self.btn_export_all.clicked.connect(self.export_all_requested.emit)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_traceroute)
        buttons.addWidget(self.btn_export)
        buttons.addWidget(self.btn_export_all)

        self.period = QComboBox()
        self.period.addItem("1 час", "1h")
        self.period.addItem("24 часа", "24h")
        self.period.addItem("72 часа", "72h")
        self.period.addItem("7 дней", "7d")
        self.period.addItem("30 дней", "30d")
        self.period.addItem("90 дней", "90d")
        self.period.currentIndexChanged.connect(self._on_period)

        self.current_period_key = "1h"

        self.chart = RttLossChart(compact=True)

        root = QVBoxLayout()
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addWidget(self.title)
        root.addWidget(self.host_label)
        root.addWidget(self.status_label)
        root.addLayout(metrics)
        root.addLayout(buttons)
        root.addWidget(self.raw_label)
        root.addWidget(self.raw_output)
        root.addWidget(self.period)
        root.addWidget(self.chart, 1)
        self.setLayout(root)

    def _on_period(self) -> None:
        key = str(self.period.currentData())
        self.current_period_key = key
        self.period_changed.emit(key)

    def set_device_details(
        self,
        *,
        name: str,
        ip: str,
        status: str,
        rtt_ms: str,
        loss_pct: str,
        last_seen: str,
        elapsed: str,
        raw_lines: Iterable[str],
    ) -> None:
        title = f"{name} ({ip})" if name else ip
        self.host_label.setText(title if title else "—")
        self.status_label.setText(f"Статус: {status}")
        self._apply_status_color(status)
        self.rtt_label.setText(f"RTT: {rtt_ms}")
        self.loss_label.setText(f"Loss: {loss_pct}")
        self.last_label.setText(f"LAST: {last_seen}")
        self.elapsed_label.setText(f"ELAPSED: {elapsed}")
        self.raw_output.setPlainText("\n".join(raw_lines) if raw_lines else "")

    def clear(self) -> None:
        self.host_label.setText("—")
        self.status_label.setText("Статус: —")
        self.rtt_label.setText("RTT: —")
        self.loss_label.setText("Loss: —")
        self.last_label.setText("LAST: —")
        self.elapsed_label.setText("ELAPSED: —")
        self.raw_output.clear()
        self._apply_status_color("UNKNOWN")

    def _apply_status_color(self, status: str) -> None:
        status = status.upper()
        pal = self.status_label.palette()
        color = None
        if status == "GREEN":
            color = Qt.green
        elif status == "YELLOW":
            color = Qt.yellow
        elif status in {"RED", "DOWN"}:
            color = Qt.red
        if color is not None:
            pal.setColor(QPalette.WindowText, color)
        else:
            pal = self.style().standardPalette()
        self.status_label.setPalette(pal)

    @staticmethod
    def format_timestamp(ts: datetime | None) -> str:
        if not ts:
            return "—"
        return ts.strftime("%Y-%m-%d %H:%M:%S")
