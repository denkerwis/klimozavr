from __future__ import annotations

from PySide6.QtWidgets import QMenuBar, QMenu, QSplitter, QWidget, QVBoxLayout
from PySide6.QtGui import QAction

from klimozawr.ui.widgets.device_cards import DeviceCardsView
from klimozawr.ui.widgets.device_details import DeviceDetailsPanel
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
        self.action_export_logs = QAction("Экспорт логов (общая)", self)
        menu_file.addAction(self.action_logout)
        menu_file.addAction(self.action_export_logs)
        menu_file.addAction(self.action_exit)
        menubar.addMenu(menu_file)
        self.setMenuBar(menubar)

        # ВАЖНО: fit_viewport=True → плитки растягиваются на весь экран
        self.cards = DeviceCardsView(fit_viewport=True, text_scale=1.15)
        self.details = DeviceDetailsPanel()

        monitor_split = QSplitter()
        monitor_split.addWidget(self.cards)
        monitor_split.addWidget(self.details)
        monitor_split.setStretchFactor(0, 3)
        monitor_split.setStretchFactor(1, 2)

        monitor_tab = QWidget()
        ml = QVBoxLayout()
        ml.addWidget(monitor_split)
        monitor_tab.setLayout(ml)

        self.setCentralWidget(monitor_tab)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
