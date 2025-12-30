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

        self.sound_down = QLineEdit()
        self.sound_up = QLineEdit()
        self.sound_warning = QLineEdit()
        self.sound_critical = QLineEdit()
        self.sound_offline = QLineEdit()

        btn_down = QPushButton(tr("settings.button.pick"))
        btn_up = QPushButton(tr("settings.button.pick"))
        btn_warning = QPushButton(tr("settings.button.pick"))
        btn_critical = QPushButton(tr("settings.button.pick"))
        btn_offline = QPushButton(tr("settings.button.pick"))
        btn_down.clicked.connect(lambda: self._pick_file(self.sound_down))
        btn_up.clicked.connect(lambda: self._pick_file(self.sound_up))
        btn_warning.clicked.connect(lambda: self._pick_file(self.sound_warning))
        btn_critical.clicked.connect(lambda: self._pick_file(self.sound_critical))
        btn_offline.clicked.connect(lambda: self._pick_file(self.sound_offline))

        row_down = QHBoxLayout()
        row_down.addWidget(self.sound_down, 1)
        row_down.addWidget(btn_down)

        row_up = QHBoxLayout()
        row_up.addWidget(self.sound_up, 1)
        row_up.addWidget(btn_up)

        row_warning = QHBoxLayout()
        row_warning.addWidget(self.sound_warning, 1)
        row_warning.addWidget(btn_warning)

        row_critical = QHBoxLayout()
        row_critical.addWidget(self.sound_critical, 1)
        row_critical.addWidget(btn_critical)

        row_offline = QHBoxLayout()
        row_offline.addWidget(self.sound_offline, 1)
        row_offline.addWidget(btn_offline)

        form = QFormLayout()
        form.addRow(tr("settings.label.sound_down_global"), row_down)
        form.addRow(tr("settings.label.sound_up_global"), row_up)
        form.addRow(tr("settings.label.sound_warning_global"), row_warning)
        form.addRow(tr("settings.label.sound_critical_global"), row_critical)
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
            self.sound_down.setText(str(initial.get("sound_down_path", "")) or "")
            self.sound_up.setText(str(initial.get("sound_up_path", "")) or "")
            self.sound_warning.setText(str(initial.get("default_warning_wav", "")) or "")
            self.sound_critical.setText(str(initial.get("default_critical_wav", "")) or "")
            self.sound_offline.setText(str(initial.get("default_offline_wav", "")) or "")

    def _pick_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("settings.file_dialog_title"), "", tr("dialog.wav_filter"))
        if path:
            target.setText(path)

    def _on_ok(self) -> None:
        for label, path in (
            (tr("settings.sound_down_label"), self.sound_down.text()),
            (tr("settings.sound_up_label"), self.sound_up.text()),
            (tr("settings.sound_warning_label"), self.sound_warning.text()),
            (tr("settings.sound_critical_label"), self.sound_critical.text()),
            (tr("settings.sound_offline_label"), self.sound_offline.text()),
        ):
            if path and not Path(path).exists():
                QMessageBox.critical(self, tr("settings.error_title"), tr("settings.error_missing_file", label=label))
                return
        self.accept()

    def payload(self) -> dict:
        return {
            "sound_down_path": self.sound_down.text().strip(),
            "sound_up_path": self.sound_up.text().strip(),
            "default_warning_wav": self.sound_warning.text().strip(),
            "default_critical_wav": self.sound_critical.text().strip(),
            "default_offline_wav": self.sound_offline.text().strip(),
        }
