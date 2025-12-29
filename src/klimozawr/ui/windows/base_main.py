from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox


class BaseMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._allow_close = False
        self.setWindowTitle("Климозавр")
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

    def allow_close(self, yes: bool) -> None:
        self._allow_close = yes

    def closeEvent(self, event) -> None:
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        QMessageBox.information(self, "Выход", "Закрытие запрещено. Выход только через меню: Файл → Выход")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.showFullScreen()
