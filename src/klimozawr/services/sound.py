from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

from klimozawr.core.alerts import RED_REPEAT

logger = logging.getLogger("klimozawr.sound")


class SoundManager:
    def __init__(self, yellow_wav: Path, red_wav: Path) -> None:
        self._yellow = QSoundEffect()
        self._red = QSoundEffect()
        self._cache: dict[tuple[str, float, int], QSoundEffect] = {}
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

    def play_path(self, wav_path: str, *, volume: float = 0.9, loop_count: int = 1) -> None:
        if not wav_path:
            return
        try:
            key = (wav_path, float(volume), int(loop_count))
            effect = self._cache.get(key)
            if effect is None:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(wav_path)))
                effect.setLoopCount(int(loop_count))
                effect.setVolume(float(volume))
                self._cache[key] = effect
            logger.info(
                "sound play file=%s volume=%s loops=%s play()",
                wav_path,
                effect.volume(),
                effect.loopCount(),
            )
            effect.play()
        except Exception:
            logger.exception("failed to play sound path=%s", wav_path)

    def beep(self, *, duration_ms: int = 500, frequency: int = 880) -> None:
        if sys.platform != "win32":
            logger.warning("beep requested on non-windows platform")
            return
        try:
            import winsound
            winsound.Beep(int(frequency), int(duration_ms))
        except Exception:
            logger.exception("failed to play system beep")


class AlertSoundManager:
    def __init__(
        self,
        sound: SoundManager,
        *,
        critical_window_secs: int = 10,
        critical_cooldown_secs: int = 60,
        warning_window_secs: int = 10,
        warning_cooldown_secs: int = 20,
    ) -> None:
        self._sound = sound
        self._critical_window = timedelta(seconds=critical_window_secs)
        self._critical_cooldown = timedelta(seconds=critical_cooldown_secs)
        self._warning_window = timedelta(seconds=warning_window_secs)
        self._warning_cooldown = timedelta(seconds=warning_cooldown_secs)
        self._critical_events: deque[tuple[datetime, int]] = deque()
        self._warning_events: deque[tuple[datetime, int]] = deque()
        self._critical_cooldown_until: datetime | None = None
        self._warning_cooldown_until: datetime | None = None
        self._last_mass_critical_played: datetime | None = None

    @staticmethod
    def _resolve_path(*candidates: str) -> str:
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)
        return ""

    def handle_alert(
        self,
        *,
        device_id: int,
        level: str,
        device_path: str,
        default_path: str,
        fallback_path: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        level = str(level).upper()
        if level == "RED":
            self._handle_critical(
                device_id=device_id,
                now=now,
                device_path=device_path,
                default_path=default_path,
                fallback_path=fallback_path,
            )
        elif level == "YELLOW":
            self._handle_warning(
                device_id=device_id,
                now=now,
                device_path=device_path,
                default_path=default_path,
                fallback_path=fallback_path,
            )

    def _handle_critical(
        self,
        *,
        device_id: int,
        now: datetime,
        device_path: str,
        default_path: str,
        fallback_path: str,
    ) -> None:
        self._critical_events.append((now, int(device_id)))
        while self._critical_events and now - self._critical_events[0][0] > self._critical_window:
            self._critical_events.popleft()

        unique_devices = {did for _ts, did in self._critical_events}
        in_mass = len(unique_devices) >= 2
        if in_mass:
            if self._last_mass_critical_played is None or now - self._last_mass_critical_played >= RED_REPEAT:
                self._play_critical_mass(now, default_path, fallback_path)
                self._critical_cooldown_until = now + self._critical_cooldown
                return
            if self._critical_cooldown_until is None or now >= self._critical_cooldown_until:
                self._critical_cooldown_until = now + self._critical_cooldown
            return

        if self._critical_cooldown_until and now < self._critical_cooldown_until:
            return

        self._critical_cooldown_until = None
        path = self._resolve_path(device_path, default_path, fallback_path)
        if path:
            self._sound.play_path(path, volume=1.0)
        else:
            self._sound.beep(duration_ms=500)

    def _play_critical_mass(self, now: datetime, default_path: str, fallback_path: str) -> None:
        path = self._resolve_path(default_path, fallback_path)
        if path:
            self._sound.play_path(path, volume=1.0)
        else:
            self._sound.beep(duration_ms=700)
        self._last_mass_critical_played = now

    def _handle_warning(
        self,
        *,
        device_id: int,
        now: datetime,
        device_path: str,
        default_path: str,
        fallback_path: str,
    ) -> None:
        self._warning_events.append((now, int(device_id)))
        while self._warning_events and now - self._warning_events[0][0] > self._warning_window:
            self._warning_events.popleft()

        unique_devices = {did for _ts, did in self._warning_events}
        in_mass = len(unique_devices) >= 2
        if in_mass:
            if self._warning_cooldown_until is None or now >= self._warning_cooldown_until:
                path = self._resolve_path(default_path, fallback_path)
                if path:
                    self._sound.play_path(path, volume=0.85)
                else:
                    self._sound.beep(duration_ms=350)
                self._warning_cooldown_until = now + self._warning_cooldown
            return

        if self._warning_cooldown_until and now < self._warning_cooldown_until:
            return

        self._warning_cooldown_until = None
        path = self._resolve_path(device_path, default_path, fallback_path)
        if path:
            self._sound.play_path(path, volume=0.85)
        else:
            self._sound.beep(duration_ms=350)
