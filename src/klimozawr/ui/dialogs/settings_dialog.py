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


class SettingsDialog(QDialog):
    def __init__(self, initial: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)

        self.sound_down = QLineEdit()
        self.sound_up = QLineEdit()

        btn_down = QPushButton("Выбрать...")
        btn_up = QPushButton("Выбрать...")
        btn_down.clicked.connect(lambda: self._pick_file(self.sound_down))
        btn_up.clicked.connect(lambda: self._pick_file(self.sound_up))

        row_down = QHBoxLayout()
        row_down.addWidget(self.sound_down, 1)
        row_down.addWidget(btn_down)

        row_up = QHBoxLayout()
        row_up.addWidget(self.sound_up, 1)
        row_up.addWidget(btn_up)

        form = QFormLayout()
        form.addRow("DOWN.wav (глобальный)", row_down)
        form.addRow("UP.wav (глобальный)", row_up)

        btn_ok = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")
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
        path, _ = QFileDialog.getOpenFileName(self, "Выбор WAV", "", "WAV Files (*.wav)")
        if path:
            target.setText(path)

    def _on_ok(self) -> None:
        for label, path in (("DOWN.wav", self.sound_down.text()), ("UP.wav", self.sound_up.text())):
            if path and not Path(path).exists():
                QMessageBox.critical(self, "Ошибка", f"{label}: файл не найден.")
                return
        self.accept()

    def payload(self) -> dict:
        return {
            "sound_down_path": self.sound_down.text().strip(),
            "sound_up_path": self.sound_up.text().strip(),
        }
