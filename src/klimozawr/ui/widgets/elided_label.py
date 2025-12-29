from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None, *, elide_mode: Qt.TextElideMode = Qt.ElideRight) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self._elide_mode = elide_mode
        self._is_elided = False
        self.setWordWrap(False)

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = text or ""
        self._update_elide()

    def fullText(self) -> str:
        return self._full_text

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self) -> None:
        width = max(0, self.contentsRect().width())
        if width <= 0:
            super().setText(self._full_text)
            self._set_elided(False)
            return

        fm = QFontMetrics(self.font())
        lines = self._full_text.splitlines() or [""]
        elided_lines: list[str] = []
        was_elided = False
        for line in lines:
            elided = fm.elidedText(line, self._elide_mode, width)
            if elided != line:
                was_elided = True
            elided_lines.append(elided)

        super().setText("\n".join(elided_lines))
        self._set_elided(was_elided)

    def _set_elided(self, enabled: bool) -> None:
        self._is_elided = enabled
        self.setToolTip(self._full_text if enabled else "")
