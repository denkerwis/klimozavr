from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
)

from klimozawr.storage.repositories import UserRepo
from klimozawr.ui.strings import tr


class CreateFirstAdminDialog(QDialog):
    def __init__(self, user_repo: UserRepo) -> None:
        super().__init__()
        self.setWindowTitle(tr("first_admin.title"))
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self._repo = user_repo

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow(tr("first_admin.username"), self.username)
        form.addRow(tr("first_admin.password"), self.password)

        btn = QPushButton(tr("first_admin.button"))
        btn.clicked.connect(self._on_create)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(btn)
        self.setLayout(layout)

    def closeEvent(self, event) -> None:
        # cannot close
        event.ignore()

    def _on_create(self) -> None:
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            QMessageBox.warning(
                self,
                tr("first_admin.validation_title"),
                tr("first_admin.validation_message"),
            )
            return
        try:
            self._repo.create_user(u, p, "admin")
        except Exception as e:
            QMessageBox.critical(self, tr("first_admin.error_title"), tr("first_admin.error_message", error=e))
            return
        self.accept()
