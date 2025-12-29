from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtMultimedia", exc_type=ImportError)

from klimozawr.services import sound as sound_module


class DummySoundEffect:
    def __init__(self) -> None:
        self.played = False
        self.source = None
        self.loop_count = None
        self.volume = None

    def setSource(self, source) -> None:
        self.source = source

    def setLoopCount(self, count: int) -> None:
        self.loop_count = count

    def setVolume(self, volume: float) -> None:
        self.volume = volume

    def play(self) -> None:
        self.played = True


def test_sound_manager_plays_levels(tmp_path, monkeypatch):
    monkeypatch.setattr(sound_module, "QSoundEffect", DummySoundEffect)

    yellow = tmp_path / "yellow.wav"
    red = tmp_path / "red.wav"
    yellow.write_bytes(b"")
    red.write_bytes(b"")

    sm = sound_module.SoundManager(Path(yellow), Path(red))
    sm.play("YELLOW")
    sm.play("RED")

    assert sm._yellow.played is True
    assert sm._red.played is True
