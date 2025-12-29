from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QLabel,
)


class TracerouteDialog(QDialog):
    def __init__(self, title: str, output: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(720, 480)

        self.lbl_title = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.lbl_title.setFont(title_font)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(output)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)

        btn_copy = QPushButton("Скопировать")
        btn_close = QPushButton("Закрыть")
        btn_copy.clicked.connect(self._copy)
        btn_close.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_copy)
        buttons.addWidget(btn_close)

        root = QVBoxLayout()
        root.addWidget(self.lbl_title)
        root.addWidget(self.text, 1)
        root.addLayout(buttons)
        self.setLayout(root)

    def _copy(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text.toPlainText(), mode=clipboard.Clipboard)
