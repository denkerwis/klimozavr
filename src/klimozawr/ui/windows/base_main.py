from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox

from klimozawr.ui.strings import tr
from klimozawr.ui.widgets.host_offline_overlay import HostOfflineOverlay

class BaseMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._allow_close = False
        self._host_overlay = HostOfflineOverlay(self)
        self._host_overlay.hide()
        self.setWindowTitle(tr("app.title"))
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

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
        self._host_overlay.sync_geometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._host_overlay.sync_geometry()

    def set_host_offline_visible(self, visible: bool) -> None:
        if visible:
            self._host_overlay.sync_geometry()
            self._host_overlay.show()
            self._host_overlay.raise_()
        else:
            self._host_overlay.hide()
