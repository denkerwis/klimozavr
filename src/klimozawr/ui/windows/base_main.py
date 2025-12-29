from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox

from klimozawr.ui.strings import tr

class BaseMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._allow_close = False
        self.setWindowTitle(tr("app.title"))
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

    def allow_close(self, yes: bool) -> None:
        self._allow_close = yes

    def closeEvent(self, event) -> None:
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        QMessageBox.information(
            self,
            tr("app.close_forbidden_title"),
            tr("app.close_forbidden_message"),
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.showFullScreen()
