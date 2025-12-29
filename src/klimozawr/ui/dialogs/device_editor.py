from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QSpinBox, QPushButton, QHBoxLayout, QMessageBox
)


def _get(initial: Any, key: str, default: Any = "") -> Any:
    if initial is None:
        return default
    if isinstance(initial, dict):
        return initial.get(key, default)
    return getattr(initial, key, default)


class DeviceEditorDialog(QDialog):
    def __init__(self, initial: Any = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Устройство")
        self.setModal(True)

        self.ip = QLineEdit()
        self.name = QLineEdit()
        self.location = QLineEdit()
        self.owner = QLineEdit()
        self.comment = QTextEdit()
        self.comment.setFixedHeight(80)

        self.yellow_to_red_secs = QSpinBox()
        self.yellow_to_red_secs.setRange(5, 3600)
        self.yellow_to_red_secs.setValue(120)

        self.yellow_notify_after_secs = QSpinBox()
        self.yellow_notify_after_secs.setRange(1, 3600)
        self.yellow_notify_after_secs.setValue(30)

        self.ping_timeout_ms = QSpinBox()
        self.ping_timeout_ms.setRange(100, 5000)
        self.ping_timeout_ms.setSingleStep(100)
        self.ping_timeout_ms.setValue(1000)

        form = QFormLayout()
        form.addRow("IP", self.ip)
        form.addRow("Имя", self.name)
        form.addRow("Локация", self.location)
        form.addRow("Владелец", self.owner)
        form.addRow("Комментарий", self.comment)
        form.addRow("yellow_to_red_secs", self.yellow_to_red_secs)
        form.addRow("yellow_notify_after_secs", self.yellow_notify_after_secs)
        form.addRow("ping_timeout_ms", self.ping_timeout_ms)

        btn_ok = QPushButton("Готово")
        btn_cancel = QPushButton("Отмена")
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)

        bh = QHBoxLayout()
        bh.addStretch(1)
        bh.addWidget(btn_ok)
        bh.addWidget(btn_cancel)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addLayout(bh)
        self.setLayout(root)

        data = {}
        if initial is None:
            data = {}
        elif isinstance(initial, dict):
            data = initial
        else:
            # Device dataclass/object
            data = {
                "ip": getattr(initial, "ip", ""),
                "name": getattr(initial, "name", ""),
                "comment": getattr(initial, "comment", ""),
                "location": getattr(initial, "location", ""),
                "owner": getattr(initial, "owner", ""),
                "yellow_to_red_secs": getattr(initial, "yellow_to_red_secs", 120),
                "yellow_notify_after_secs": getattr(initial, "yellow_notify_after_secs", 30),
                "ping_timeout_ms": getattr(initial, "ping_timeout_ms", 1000),
            }


        # preload (dict or Device)
        self.ip.setText(str(_get(data.get, "ip", "")) or "")
        self.name.setText(str(_get(data.get, "name", "")) or "")
        self.location.setText(str(_get(data.get, "location", "")) or "")
        self.owner.setText(str(_get(data.get, "owner", "")) or "")
        self.comment.setPlainText(str(_get(data.get, "comment", "")) or "")

        self.yellow_to_red_secs.setValue(int(_get(data.get, "yellow_to_red_secs", 120) or 120))
        self.yellow_notify_after_secs.setValue(int(_get(data.get, "yellow_notify_after_secs", 30) or 30))
        self.ping_timeout_ms.setValue(int(_get(data.get, "ping_timeout_ms", 1000) or 1000))

    def _on_ok(self) -> None:
        ip = self.ip.text().strip()
        if not ip:
            QMessageBox.critical(self, "Ошибка", "IP обязателен.")
            return
        self.accept()

    def payload(self) -> dict:
        return {
            "ip": self.ip.text().strip(),
            "name": self.name.text().strip(),
            "comment": self.comment.toPlainText().strip(),
            "location": self.location.text().strip(),
            "owner": self.owner.text().strip(),
            "yellow_to_red_secs": int(self.yellow_to_red_secs.value()),
            "yellow_notify_after_secs": int(self.yellow_notify_after_secs.value()),
            "ping_timeout_ms": int(self.ping_timeout_ms.value()),
        }
