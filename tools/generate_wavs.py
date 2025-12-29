from __future__ import annotations

import math
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOUNDS = ROOT / "resources" / "sounds"


def write_beep(path: Path, freq_hz: float, duration_s: float, volume: float = 0.3, sample_rate: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    n = int(sample_rate * duration_s)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            # simple sine with soft attack/decay
            env = 1.0
            attack = 0.01
            decay = 0.08
            if t < attack:
                env = t / attack
            elif t > duration_s - decay:
                env = max(0.0, (duration_s - t) / decay)
            s = math.sin(2.0 * math.pi * freq_hz * t) * volume * env
            v = int(max(-1.0, min(1.0, s)) * 32767)
            frames += int(v).to_bytes(2, byteorder="little", signed=True)

        wf.writeframes(frames)


def main() -> None:
    yellow = SOUNDS / "yellow.wav"
    red = SOUNDS / "red.wav"

    # regenerate if missing
    if not yellow.exists():
        write_beep(yellow, freq_hz=880.0, duration_s=0.18, volume=0.35)
        print(f"generated: {yellow}")

    if not red.exists():
        write_beep(red, freq_hz=220.0, duration_s=0.35, volume=0.45)
        print(f"generated: {red}")

    if yellow.exists() and red.exists():
        print("sounds OK")


if __name__ == "__main__":
    main()
