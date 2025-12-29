from __future__ import annotations

from PySide6.QtWidgets import QMenuBar, QMenu, QWidget, QVBoxLayout
from PySide6.QtGui import QAction

from klimozawr.ui.widgets.device_cards import DeviceCardsView
from klimozawr.ui.windows.base_main import BaseMainWindow
from klimozawr.ui.strings import tr


class UserMainWindow(BaseMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app.title_user"))
        self.setWindowState(self.windowState())  # no-op, but keeps pattern

        menubar = QMenuBar()
        menu_file = QMenu(tr("menu.title"), self)
        self.action_logout = QAction(tr("menu.logout"), self)
        self.action_exit = QAction(tr("menu.exit"), self)
        menu_file.addAction(self.action_logout)
        menu_file.addAction(self.action_exit)
        menubar.addMenu(menu_file)
        self.setMenuBar(menubar)

        # ВАЖНО: fit_viewport=True → адаптивная сетка плиток по ширине окна
        self.cards = DeviceCardsView(
            fit_viewport=True,
            base_tile_px=360,
            spacing=20,
            margins=20,
            text_scale=1.45,
            min_tile_px=300,
            max_tile_px=520,
        )

        monitor_tab = QWidget()
        ml = QVBoxLayout()
        ml.addWidget(self.cards)
        monitor_tab.setLayout(ml)

        self.setCentralWidget(monitor_tab)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
