from __future__ import annotations

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction

from klimozawr.ui.widgets.device_cards import DeviceCardsView
from klimozawr.ui.windows.base_main import BaseMainWindow


class UserMainWindow(BaseMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("klimozawr (User)")
        self.setWindowState(self.windowState())  # no-op, but keeps pattern

        menubar = QMenuBar()
        menu_file = QMenu("Меню", self)
        self.action_logout = QAction("Выйти из аккаунта", self)
        self.action_exit = QAction("Выход", self)
        menu_file.addAction(self.action_logout)
        menu_file.addAction(self.action_exit)
        menubar.addMenu(menu_file)
        self.setMenuBar(menubar)

        # ВАЖНО: fit_viewport=True → плитки растягиваются на весь экран
        self.cards = DeviceCardsView(fit_viewport=True)
        self.setCentralWidget(self.cards)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
