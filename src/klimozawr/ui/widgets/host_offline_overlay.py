from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame

from klimozawr.ui.strings import tr


class HostOfflineOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame()
        panel.setObjectName("hostOfflinePanel")
        panel.setStyleSheet(
            "#hostOfflinePanel {"
            "background-color: rgba(20, 20, 20, 200);"
            "border-radius: 12px;"
            "padding: 16px 24px;"
            "}"
        )
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(18, 14, 18, 14)
        panel_layout.setSpacing(6)

        title = QLabel(tr("host_offline.title"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")

        subtitle = QLabel(tr("host_offline.subtitle"))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #e6e6e6; font-size: 13px;")

        panel_layout.addWidget(title)
        panel_layout.addWidget(subtitle)
        panel.setLayout(panel_layout)

        root.addWidget(panel, 0, Qt.AlignHCenter)
        root.addStretch(2)
        self.setLayout(root)

    def sync_geometry(self) -> None:
        parent = self.parentWidget()
        if parent:
            self.setGeometry(0, 0, parent.width(), parent.height())
