from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QComboBox, QVBoxLayout
)


@dataclass(frozen=True)
class NewUserPayload:
    username: str
    password: str
    role: str  # "admin" | "user"


class CreateUserDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создать пользователя")
        self.setModal(True)

        self._payload: NewUserPayload | None = None

        self.ed_username = QLineEdit()
        self.ed_password = QLineEdit()
        self.ed_password.setEchoMode(QLineEdit.Password)
        self.ed_password2 = QLineEdit()
        self.ed_password2.setEchoMode(QLineEdit.Password)

        self.cb_role = QComboBox()
        self.cb_role.addItems(["user", "admin"])
        self.cb_role.setCurrentText("user")

        form = QFormLayout()
        form.addRow("Логин *", self.ed_username)
        form.addRow("Роль", self.cb_role)
        form.addRow("Пароль *", self.ed_password)
        form.addRow("Повтор пароля *", self.ed_password2)

        hint = QLabel("Поля со * обязательны.")
        hint.setStyleSheet("opacity: 0.75;")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
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
        role = self.cb_role.currentText().strip()

        if not username:
            QMessageBox.warning(self, "Проверка", "Логин обязателен.")
            return
        if role not in ("admin", "user"):
            QMessageBox.warning(self, "Проверка", "Некорректная роль.")
            return
        if not pw1:
            QMessageBox.warning(self, "Проверка", "Пароль обязателен.")
            return
        if pw1 != pw2:
            QMessageBox.warning(self, "Проверка", "Пароли не совпадают.")
            return

        self._payload = NewUserPayload(username=username, password=pw1, role=role)
        self.accept()

    def payload(self) -> NewUserPayload:
        assert self._payload is not None
        return self._payload


class SetPasswordDialog(QDialog):
    def __init__(self, username: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Сменить пароль: {username}")
        self.setModal(True)
        self._password: str | None = None

        self.ed_password = QLineEdit()
        self.ed_password.setEchoMode(QLineEdit.Password)
        self.ed_password2 = QLineEdit()
        self.ed_password2.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Новый пароль *", self.ed_password)
        form.addRow("Повтор *", self.ed_password2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
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
            QMessageBox.warning(self, "Проверка", "Пароль обязателен.")
            return
        if pw1 != pw2:
            QMessageBox.warning(self, "Проверка", "Пароли не совпадают.")
            return
        self._password = pw1
        self.accept()

    def password(self) -> str:
        assert self._password is not None
        return self._password
