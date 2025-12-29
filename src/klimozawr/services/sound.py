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
        self._yellow_path = str(yellow_wav)
        self._red_path = str(red_wav)
        self._yellow_volume = 0.8
        self._red_volume = 1.0

        self._yellow.setSource(QUrl.fromLocalFile(self._yellow_path))
        self._red.setSource(QUrl.fromLocalFile(self._red_path))

        self._yellow.setLoopCount(1)
        self._red.setLoopCount(1)
        self._yellow.setVolume(self._yellow_volume)
        self._red.setVolume(self._red_volume)

    def play(self, level: str) -> None:
        try:
            if level == "YELLOW":
                logger.info(
                    "sound alert level=%s file=%s volume=%s play()",
                    level,
                    self._yellow_path,
                    self._yellow_volume,
                )
                self._yellow.play()
            elif level == "RED":
                logger.info(
                    "sound alert level=%s file=%s volume=%s play()",
                    level,
                    self._red_path,
                    self._red_volume,
                )
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
            logger.info("sound play file=%s volume=%s play()", wav_path, effect.volume())
            effect.play()
        except Exception:
            logger.exception("failed to play sound path=%s", wav_path)
