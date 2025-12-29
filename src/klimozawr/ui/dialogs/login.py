from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
)

from klimozawr.storage.repositories import UserRepo


class LoginDialog(QDialog):
    logged_in = Signal(dict)  # user dict

    def __init__(self, user_repo: UserRepo) -> None:
        super().__init__()
        self.setWindowTitle("Вход")
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self._repo = user_repo

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Имя:", self.username)
        form.addRow("Пароль:", self.password)

        btn = QPushButton("Войти")
        btn.clicked.connect(self._on_login)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(btn)
        self.setLayout(layout)

    def closeEvent(self, event) -> None:
        # cannot close login (reopens forever by design)
        event.ignore()
        QMessageBox.information(self, "Login", "Close is disabled. Please login.")

    def _on_login(self) -> None:
        u = self.username.text().strip()
        p = self.password.text()
        user = self._repo.verify_login(u, p)
        if not user:
            QMessageBox.warning(self, "Login", "Invalid credentials.")
            return
        self.logged_in.emit(user)
        self.accept()
