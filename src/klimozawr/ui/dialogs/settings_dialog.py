from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
)

from klimozawr.ui.strings import tr

class SettingsDialog(QDialog):
    def __init__(self, initial: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.setModal(True)

        self.default_up = QLineEdit()
        self.default_unstable = QLineEdit()
        self.default_down = QLineEdit()
        self.default_offline = QLineEdit()

        btn_up = QPushButton(tr("settings.button.pick"))
        btn_unstable = QPushButton(tr("settings.button.pick"))
        btn_down = QPushButton(tr("settings.button.pick"))
        btn_offline = QPushButton(tr("settings.button.pick"))
        btn_up.clicked.connect(lambda: self._pick_file(self.default_up))
        btn_unstable.clicked.connect(lambda: self._pick_file(self.default_unstable))
        btn_down.clicked.connect(lambda: self._pick_file(self.default_down))
        btn_offline.clicked.connect(lambda: self._pick_file(self.default_offline))

        row_up = QHBoxLayout()
        row_up.addWidget(self.default_up, 1)
        row_up.addWidget(btn_up)

        row_unstable = QHBoxLayout()
        row_unstable.addWidget(self.default_unstable, 1)
        row_unstable.addWidget(btn_unstable)

        row_down = QHBoxLayout()
        row_down.addWidget(self.default_down, 1)
        row_down.addWidget(btn_down)

        row_offline = QHBoxLayout()
        row_offline.addWidget(self.default_offline, 1)
        row_offline.addWidget(btn_offline)

        form = QFormLayout()
        form.addRow(tr("settings.label.sound_up_global"), row_up)
        form.addRow(tr("settings.label.sound_unstable_global"), row_unstable)
        form.addRow(tr("settings.label.sound_down_global"), row_down)
        form.addRow(tr("settings.label.sound_offline_global"), row_offline)

        btn_ok = QPushButton(tr("settings.button.save"))
        btn_cancel = QPushButton(tr("settings.button.cancel"))
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addLayout(buttons)
        self.setLayout(root)

        if initial:
            self.default_up.setText(str(initial.get("default_up_wav", "")) or "")
            self.default_unstable.setText(str(initial.get("default_unstable_wav", "")) or "")
            self.default_down.setText(str(initial.get("default_down_wav", "")) or "")
            self.default_offline.setText(str(initial.get("default_offline_wav", "")) or "")

    def _pick_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("settings.file_dialog_title"), "", tr("dialog.wav_filter"))
        if path:
            target.setText(path)

    def _on_ok(self) -> None:
        for label, path in (
            (tr("settings.sound_up_label"), self.default_up.text()),
            (tr("settings.sound_unstable_label"), self.default_unstable.text()),
            (tr("settings.sound_down_label"), self.default_down.text()),
            (tr("settings.sound_offline_label"), self.default_offline.text()),
        ):
            if path and not Path(path).exists():
                QMessageBox.critical(self, tr("settings.error_title"), tr("settings.error_missing_file", label=label))
                return
        self.accept()

    def payload(self) -> dict:
        return {
            "default_up_wav": self.default_up.text().strip(),
            "default_unstable_wav": self.default_unstable.text().strip(),
            "default_down_wav": self.default_down.text().strip(),
            "default_offline_wav": self.default_offline.text().strip(),
        }
