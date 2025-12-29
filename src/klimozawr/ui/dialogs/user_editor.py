from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QComboBox, QVBoxLayout
)

from klimozawr.ui.strings import role_display, tr

@dataclass(frozen=True)
class NewUserPayload:
    username: str
    password: str
    role: str  # "admin" | "user"


class CreateUserDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("user.create_title"))
        self.setModal(True)

        self._payload: NewUserPayload | None = None

        self.ed_username = QLineEdit()
        self.ed_password = QLineEdit()
        self.ed_password.setEchoMode(QLineEdit.Password)
        self.ed_password2 = QLineEdit()
        self.ed_password2.setEchoMode(QLineEdit.Password)

        self.cb_role = QComboBox()
        self.cb_role.addItem(role_display("user"), "user")
        self.cb_role.addItem(role_display("admin"), "admin")
        self.cb_role.setCurrentIndex(0)

        form = QFormLayout()
        form.addRow(tr("user.field.username"), self.ed_username)
        form.addRow(tr("user.field.role"), self.cb_role)
        form.addRow(tr("user.field.password"), self.ed_password)
        form.addRow(tr("user.field.password_repeat"), self.ed_password2)

        hint = QLabel(tr("user.hint_required_fields"))
        hint.setStyleSheet("opacity: 0.75;")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("user.button.create"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("user.button.cancel"))
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addWidget(hint)
        root.addWidget(buttons)
        self.setLayout(root)

    def _on_accept(self) -> None:
        username = self.ed_username.text().strip()
        pw1 = self.ed_password.text()
        pw2 = self.ed_password2.text()
        role = str(self.cb_role.currentData()).strip()

        if not username:
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_username_required"))
            return
        if role not in ("admin", "user"):
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_role_invalid"))
            return
        if not pw1:
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_password_required"))
            return
        if pw1 != pw2:
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_passwords_mismatch"))
            return

        self._payload = NewUserPayload(username=username, password=pw1, role=role)
        self.accept()

    def payload(self) -> NewUserPayload:
        assert self._payload is not None
        return self._payload


class SetPasswordDialog(QDialog):
    def __init__(self, username: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("user.set_password_title", username=username))
        self.setModal(True)
        self._password: str | None = None

        self.ed_password = QLineEdit()
        self.ed_password.setEchoMode(QLineEdit.Password)
        self.ed_password2 = QLineEdit()
        self.ed_password2.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow(tr("user.field.password_new"), self.ed_password)
        form.addRow(tr("user.field.password_repeat_short"), self.ed_password2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("user.button.save"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("user.button.cancel"))
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addWidget(buttons)
        self.setLayout(root)

    def _on_accept(self) -> None:
        pw1 = self.ed_password.text()
        pw2 = self.ed_password2.text()
        if not pw1:
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_password_required"))
            return
        if pw1 != pw2:
            QMessageBox.warning(self, tr("user.validation_title"), tr("user.validation_passwords_mismatch"))
            return
        self._password = pw1
        self.accept()

    def password(self) -> str:
        assert self._password is not None
        return self._password
