from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout, QMenuBar, QMenu,
    QTabWidget, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from PySide6.QtGui import QAction

from klimozawr.ui.windows.base_main import BaseMainWindow
from klimozawr.ui.widgets.device_cards import DeviceCardsView
from klimozawr.ui.widgets.device_details import DeviceDetailsPanel
from klimozawr.ui.widgets.alerts_panel import AlertsPanel


class AdminMainWindow(BaseMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.menu = QMenuBar()
        file_menu = QMenu("Меню", self)
        self.action_logout = QAction("Выйти из аккаунта", self)
        self.action_exit = QAction("Выход", self)
        self.action_export_logs = QAction("Экспорт логов (общая)", self)
        self.action_settings = QAction("Настройки", self)
        file_menu.addAction(self.action_logout)
        file_menu.addAction(self.action_export_logs)
        file_menu.addAction(self.action_settings)
        file_menu.addAction(self.action_exit)
        self.menu.addMenu(file_menu)
        self.setMenuBar(self.menu)

        # monitor tab = user-like UI
        self.cards = DeviceCardsView(fit_viewport=False)
        self.details = DeviceDetailsPanel()
        self.alerts = AlertsPanel()

        monitor_right = QWidget()
        rv = QVBoxLayout()
        rv.addWidget(self.details, 3)
        rv.addWidget(self.alerts, 2)
        monitor_right.setLayout(rv)

        monitor_split = QSplitter()
        monitor_split.addWidget(self.cards)
        monitor_split.addWidget(monitor_right)
        monitor_split.setStretchFactor(0, 3)
        monitor_split.setStretchFactor(1, 2)

        monitor_tab = QWidget()
        ml = QVBoxLayout()
        ml.addWidget(monitor_split)
        monitor_tab.setLayout(ml)

        # devices tab
        self.devices_list = QListWidget()
        self.btn_dev_add = QPushButton("Добавить")
        self.btn_dev_edit = QPushButton("Изменить")
        self.btn_dev_del = QPushButton("Удалить")
        self.btn_dev_import = QPushButton("Импорт CSV")
        self.btn_dev_export = QPushButton("Экспорт CSV")

        dev_btns = QHBoxLayout()
        for b in [self.btn_dev_add, self.btn_dev_edit, self.btn_dev_del, self.btn_dev_import, self.btn_dev_export]:
            dev_btns.addWidget(b)

        devices_tab = QWidget()
        dl = QVBoxLayout()
        dl.addLayout(dev_btns)
        dl.addWidget(self.devices_list, 1)
        devices_tab.setLayout(dl)

        # users tab
        self.users_list = QListWidget()
        self.btn_usr_add = QPushButton("Создать пользователя")
        self.btn_usr_del = QPushButton("Удалить")
        self.btn_usr_pass = QPushButton("Сменить пароль")
        self.btn_usr_role = QPushButton("Сменить роль")

        usr_btns = QHBoxLayout()
        for b in [self.btn_usr_add, self.btn_usr_del, self.btn_usr_pass, self.btn_usr_role]:
            usr_btns.addWidget(b)

        users_tab = QWidget()
        ul = QVBoxLayout()
        ul.addLayout(usr_btns)
        ul.addWidget(self.users_list, 1)
        users_tab.setLayout(ul)

        self.tabs = QTabWidget()
        self.tabs.addTab(monitor_tab, "Мониторинг")
        self.tabs.addTab(devices_tab, "Устройства")
        self.tabs.addTab(users_tab, "Пользователи")

        self.setCentralWidget(self.tabs)

