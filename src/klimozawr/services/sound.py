from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger("klimozawr.sound")


class SoundManager:
    def __init__(self, yellow_wav: Path, red_wav: Path, offline_wav: Path | None = None) -> None:
        self._yellow = QSoundEffect()
        self._red = QSoundEffect()
        self._offline = QSoundEffect() if offline_wav else None
        self._cache: dict[str, QSoundEffect] = {}
        self._yellow_path = str(yellow_wav)
        self._red_path = str(red_wav)
        self._offline_path = str(offline_wav) if offline_wav else ""
        self._yellow_volume = 0.8
        self._red_volume = 1.0
        self._offline_volume = 1.0

        self._yellow.setSource(QUrl.fromLocalFile(self._yellow_path))
        self._red.setSource(QUrl.fromLocalFile(self._red_path))
        if self._offline:
            self._offline.setSource(QUrl.fromLocalFile(self._offline_path))

        self._yellow.setLoopCount(1)
        self._red.setLoopCount(1)
        self._yellow.setVolume(self._yellow_volume)
        self._red.setVolume(self._red_volume)
        if self._offline:
            self._offline.setLoopCount(1)
            self._offline.setVolume(self._offline_volume)

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

    def play_path(self, wav_path: str, *, volume: float = 0.9) -> None:
        if not wav_path:
            return
        try:
            effect = self._cache.get(wav_path)
            if effect is None:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(wav_path)))
                effect.setLoopCount(1)
                effect.setVolume(volume)
                self._cache[wav_path] = effect
            effect.setVolume(volume)
            logger.info("sound play file=%s volume=%s play()", wav_path, effect.volume())
            effect.play()
        except Exception:
            logger.exception("failed to play sound path=%s", wav_path)

    def play_offline(self) -> None:
        if not self._offline:
            return
        try:
            logger.info(
                "sound offline file=%s volume=%s play()",
                self._offline_path,
                self._offline_volume,
            )
            self._offline.play()
        except Exception:
            logger.exception("failed to play offline sound")
