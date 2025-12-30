from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox, QLabel

from klimozawr.ui.strings import tr

class BaseMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._allow_close = False
        self.setWindowTitle(tr("app.title"))
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self._offline_overlay = QLabel(tr("host_offline.overlay"), self)
        self._offline_overlay.setAlignment(Qt.AlignCenter)
        self._offline_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 170);"
            "color: white;"
            "font-size: 32px;"
            "font-weight: bold;"
        )
        self._offline_overlay.hide()

    def allow_close(self, yes: bool) -> None:
        self._allow_close = yes

    def request_programmatic_close(self) -> None:
        self._allow_close = True
        self.close()

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
        self._sync_overlay_geometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_overlay_geometry()

    def _sync_overlay_geometry(self) -> None:
        self._offline_overlay.setGeometry(self.rect())

    def set_offline_overlay_visible(self, visible: bool) -> None:
        if visible:
            self._offline_overlay.show()
            self._offline_overlay.raise_()
        else:
            self._offline_overlay.hide()
