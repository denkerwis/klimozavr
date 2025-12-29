from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
)

from klimozawr.ui.strings import tr

def _get(initial: Any, key: str, default: Any = "") -> Any:
    if initial is None:
        return default
    if isinstance(initial, dict):
        return initial.get(key, default)
    return getattr(initial, key, default)


class DeviceEditorDialog(QDialog):
    def __init__(self, initial: Any = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("device_editor.title"))
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

        self.icon_path = QLineEdit()
        self.icon_scale = QSpinBox()
        self.icon_scale.setRange(50, 200)
        self.icon_scale.setValue(100)

        self.sound_down_path = QLineEdit()
        self.sound_up_path = QLineEdit()

        btn_icon = QPushButton(tr("device_editor.button.pick"))
        btn_sound_down = QPushButton(tr("device_editor.button.pick"))
        btn_sound_up = QPushButton(tr("device_editor.button.pick"))
        btn_icon.clicked.connect(lambda: self._pick_file(self.icon_path, tr("dialog.png_filter")))
        btn_sound_down.clicked.connect(lambda: self._pick_file(self.sound_down_path, tr("dialog.wav_filter")))
        btn_sound_up.clicked.connect(lambda: self._pick_file(self.sound_up_path, tr("dialog.wav_filter")))

        row_icon = QHBoxLayout()
        row_icon.addWidget(self.icon_path, 1)
        row_icon.addWidget(btn_icon)

        row_down = QHBoxLayout()
        row_down.addWidget(self.sound_down_path, 1)
        row_down.addWidget(btn_sound_down)

        row_up = QHBoxLayout()
        row_up.addWidget(self.sound_up_path, 1)
        row_up.addWidget(btn_sound_up)

        form = QFormLayout()
        form.addRow(tr("device_editor.label.ip"), self.ip)
        form.addRow(tr("device_editor.label.name"), self.name)
        form.addRow(tr("device_editor.label.location"), self.location)
        form.addRow(tr("device_editor.label.owner"), self.owner)
        form.addRow(tr("device_editor.label.comment"), self.comment)
        form.addRow(tr("device_editor.label.yellow_to_red_secs"), self.yellow_to_red_secs)
        form.addRow(tr("device_editor.label.yellow_notify_after_secs"), self.yellow_notify_after_secs)
        form.addRow(tr("device_editor.label.ping_timeout_ms"), self.ping_timeout_ms)
        form.addRow(tr("device_editor.label.icon"), row_icon)
        form.addRow(tr("device_editor.label.icon_scale"), self.icon_scale)
        form.addRow(tr("device_editor.label.sound_down"), row_down)
        form.addRow(tr("device_editor.label.sound_up"), row_up)

        btn_ok = QPushButton(tr("device_editor.button.ok"))
        btn_cancel = QPushButton(tr("device_editor.button.cancel"))
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
                "icon_path": getattr(initial, "icon_path", ""),
                "icon_scale": getattr(initial, "icon_scale", 100),
                "sound_down_path": getattr(initial, "sound_down_path", ""),
                "sound_up_path": getattr(initial, "sound_up_path", ""),
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
        self.icon_path.setText(str(_get(data.get, "icon_path", "")) or "")
        self.icon_scale.setValue(int(_get(data.get, "icon_scale", 100) or 100))
        self.sound_down_path.setText(str(_get(data.get, "sound_down_path", "")) or "")
        self.sound_up_path.setText(str(_get(data.get, "sound_up_path", "")) or "")

    def _on_ok(self) -> None:
        ip = self.ip.text().strip()
        if not ip:
            QMessageBox.critical(self, tr("device_editor.validation_title"), tr("device_editor.validation_ip_required"))
            return
        self.accept()

    def _pick_file(self, target: QLineEdit, filter_text: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("device_editor.file_dialog_title"), "", filter_text)
        if path:
            target.setText(path)

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
            "icon_path": self.icon_path.text().strip(),
            "icon_scale": int(self.icon_scale.value()),
            "sound_down_path": self.sound_down_path.text().strip(),
            "sound_up_path": self.sound_up_path.text().strip(),
        }
