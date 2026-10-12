"""Arayüzden bağımsız zamanlayıcı mantığı (Süreölçer ve Pomodoro).

Bu sınıf tkinter'a bağlı değildir; arayüz düzenli aralıklarla `tick()`
çağırır ve dönen olaylara göre ses çalar / kayıt yazar. Süre ölçümü
`time.monotonic()` ile yapıldığı için `after` gecikmelerinden etkilenmez.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class TimerMode(Enum):
    STOPWATCH = "stopwatch"
    POMODORO = "pomodoro"


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class Phase(Enum):
    WORK = "work"
    BREAK = "break"


@dataclass
class TimerEvent:
    kind: str                 # "work_finished" | "break_finished"
    seconds_to_log: int = 0


class TimerEngine:
    def __init__(self, work_minutes: int = 50, break_minutes: int = 10, clock=time.monotonic):
        self._clock = clock
        self.mode = TimerMode.POMODORO
        self.state = TimerState.IDLE
        self.phase = Phase.WORK
        self.work_minutes = work_minutes
        self.break_minutes = break_minutes
        self._accumulated = 0.0
        self._started_at: float | None = None
        self._phase_target = work_minutes * 60  # o anki fazın hedefi (faz başında sabitlenir)

    # ------------------------------------------------------------ ayarlar
    def set_durations(self, work_minutes: int, break_minutes: int) -> None:
        """Yeni süreler bir sonraki fazdan itibaren geçerli olur."""
        self.work_minutes = work_minutes
        self.break_minutes = break_minutes
        if self.state == TimerState.IDLE:
            self._phase_target = self._target_for(self.phase)

    def set_mode(self, mode: TimerMode) -> None:
        if self.state != TimerState.IDLE:
            raise RuntimeError("Zamanlayıcı çalışırken mod değiştirilemez.")
        self.mode = mode
        self._reset(Phase.WORK)

    # ------------------------------------------------------------ sorgular
    @property
    def is_active(self) -> bool:
        return self.state != TimerState.IDLE

    def elapsed(self) -> float:
        running = self._clock() - self._started_at if self._started_at is not None else 0.0
        return self._accumulated + running

    def remaining(self) -> float:
        return max(0.0, self._phase_target - self.elapsed())

    def display_seconds(self) -> float:
        if self.mode == TimerMode.STOPWATCH:
            return self.elapsed()
        return self.remaining()

    def progress(self) -> float:
        if self.mode == TimerMode.STOPWATCH or self._phase_target <= 0:
            return 0.0
        return min(1.0, self.elapsed() / self._phase_target)

    # ------------------------------------------------------------ eylemler
    def primary_action(self) -> None:
        """Tek buton mantığı: Başlat -> Duraklat -> Devam Et -> Duraklat ..."""
        if self.state == TimerState.IDLE:
            self._resume()
        elif self.state == TimerState.RUNNING:
            self._pause()
        else:
            self._resume()

    def finish(self) -> int:
        """Oturumu bitirir; kaydedilecek çalışma süresini (sn) döndürür.

        Mola sırasında bitirilirse mola atlanır ve 0 döner (çalışma zaten kaydedildi).
        """
        seconds = int(self.elapsed()) if self.phase == Phase.WORK else 0
        self._reset(Phase.WORK)
        return seconds

    def tick(self) -> TimerEvent | None:
        """Düzenli çağrılır; Pomodoro fazı bittiyse olay döndürür."""
        if self.mode != TimerMode.POMODORO or self.state != TimerState.RUNNING:
            return None
        if self.elapsed() < self._phase_target:
            return None
        if self.phase == Phase.WORK:
            worked = int(round(self._phase_target))
            self._reset(Phase.BREAK)
            self._resume()  # mola otomatik başlar
            return TimerEvent("work_finished", worked)
        self._reset(Phase.WORK)  # mola bitti, yeni pomodoro için hazır
        return TimerEvent("break_finished")

    # ------------------------------------------------------------ iç
    def _target_for(self, phase: Phase) -> int:
        return (self.work_minutes if phase == Phase.WORK else self.break_minutes) * 60

    def _resume(self) -> None:
        self._started_at = self._clock()
        self.state = TimerState.RUNNING

    def _pause(self) -> None:
        self._accumulated = self.elapsed()
        self._started_at = None
        self.state = TimerState.PAUSED

    def _reset(self, phase: Phase) -> None:
        self.phase = phase
        self.state = TimerState.IDLE
        self._accumulated = 0.0
        self._started_at = None
        self._phase_target = self._target_for(phase)
