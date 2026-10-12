"""Kısa uyarı melodileri (Windows'ta winsound, diğer sistemlerde sistem zili)."""
from __future__ import annotations

import threading
from typing import Callable

try:
    import winsound
except ImportError:  # Windows dışı
    winsound = None

# (frekans Hz, süre ms)
MELODIES = {
    # Çalışma bitti: yükselen Do-Mi-Sol-Do
    "work_finished": [(523, 140), (659, 140), (784, 140), (1047, 320)],
    # Mola bitti: Sol-Mi-Do ve tekrar yukarı
    "break_finished": [(784, 140), (659, 140), (523, 140), (659, 140), (784, 300)],
}


def play_melody(kind: str = "work_finished", fallback: Callable[[], None] | None = None) -> None:
    """Melodiyi arayüzü dondurmadan (ayrı iş parçacığında) çalar."""
    notes = MELODIES.get(kind, MELODIES["work_finished"])
    if winsound is None:
        if fallback:
            fallback()
        return

    def _run() -> None:
        for freq, duration in notes:
            try:
                winsound.Beep(freq, duration)
            except RuntimeError:  # bazı sistemlerde Beep desteklenmez
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                break

    threading.Thread(target=_run, daemon=True).start()
