from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger("klimozawr.sound")


class SoundManager:
    def __init__(self, yellow_wav: Path, red_wav: Path) -> None:
        self._yellow = QSoundEffect()
        self._red = QSoundEffect()
        self._cache: dict[str, QSoundEffect] = {}

        self._yellow.setSource(QUrl.fromLocalFile(str(yellow_wav)))
        self._red.setSource(QUrl.fromLocalFile(str(red_wav)))

        self._yellow.setLoopCount(1)
        self._red.setLoopCount(1)
        self._yellow.setVolume(0.9)
        self._red.setVolume(0.9)

    def play(self, level: str) -> None:
        try:
            if level == "YELLOW":
                self._yellow.play()
            elif level == "RED":
                self._red.play()
        except Exception:
            logger.exception("failed to play sound")

    def play_path(self, wav_path: str) -> None:
        if not wav_path:
            return
        try:
            effect = self._cache.get(wav_path)
            if effect is None:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(wav_path)))
                effect.setLoopCount(1)
                effect.setVolume(0.9)
                self._cache[wav_path] = effect
            effect.play()
        except Exception:
            logger.exception("failed to play sound path=%s", wav_path)
