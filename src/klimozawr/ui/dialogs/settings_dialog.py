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

        btn_down = QPushButton(tr("settings.button.pick"))
        btn_up = QPushButton(tr("settings.button.pick"))
        btn_down.clicked.connect(lambda: self._pick_file(self.sound_down))
        btn_up.clicked.connect(lambda: self._pick_file(self.sound_up))

        row_down = QHBoxLayout()
        row_down.addWidget(self.sound_down, 1)
        row_down.addWidget(btn_down)

        row_up = QHBoxLayout()
        row_up.addWidget(self.sound_up, 1)
        row_up.addWidget(btn_up)

        form = QFormLayout()
        form.addRow(tr("settings.label.sound_down_global"), row_down)
        form.addRow(tr("settings.label.sound_up_global"), row_up)

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

    def _pick_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("settings.file_dialog_title"), "", tr("dialog.wav_filter"))
        if path:
            target.setText(path)

    def _on_ok(self) -> None:
        for label, path in (
            (tr("settings.sound_down_label"), self.sound_down.text()),
            (tr("settings.sound_up_label"), self.sound_up.text()),
        ):
            if path and not Path(path).exists():
                QMessageBox.critical(self, tr("settings.error_title"), tr("settings.error_missing_file", label=label))
                return
        self.accept()

    def payload(self) -> dict:
        return {
            "sound_down_path": self.sound_down.text().strip(),
            "sound_up_path": self.sound_up.text().strip(),
        }
