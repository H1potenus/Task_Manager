"""Ana pencere: üst çubuk + sol (görevler) ve sağ (zamanlayıcı) paneller."""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ..database import Database
from ..utils import format_long_date, resource_path
from . import theme
from .settings_window import SettingsWindow
from .stats_window import StatsWindow
from .task_panel import TaskPanel
from .timer_panel import TimerPanel

APP_TITLE = "Task Planner / Pomodoro Timer"


class MainWindow(ctk.CTk):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.title(APP_TITLE)
        self.geometry("1200x700")
        self.minsize(960, 600)
        self._set_icon()
        self._stats_win: StatsWindow | None = None
        self._settings_win: SettingsWindow | None = None
        self._last_title = APP_TITLE
        self._today = date.today()

        self.grid_columnconfigure(0, weight=3, uniform="panel")
        self.grid_columnconfigure(1, weight=2, uniform="panel")
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self.task_panel = TaskPanel(self, db, lambda: db.get_int_setting("deadline_warning_days"))
        self.task_panel.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self.timer_panel = TimerPanel(self, db, self._set_title_status)
        self.timer_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60_000, self._check_day_change)

    def _set_icon(self) -> None:
        """Pencere/görev çubuğu simgesi (customtkinter başlangıçta kendi simgesini koyduğu için gecikmeli)."""
        ico = resource_path("assets/icon.ico")
        if not ico.exists():
            return

        def apply() -> None:
            try:
                self.iconbitmap(str(ico))
            except Exception:  # Windows dışı sistemlerde .ico desteklenmeyebilir
                pass

        apply()
        self.after(250, apply)

    def _build_top_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 10))
        ctk.CTkLabel(bar, text=APP_TITLE, font=theme.font(24, "bold")).pack(side="left")
        self.date_label = ctk.CTkLabel(bar, text=format_long_date(date.today(), with_day=True),
                                       font=theme.font(13), text_color=theme.MUTED_TEXT)
        self.date_label.pack(side="left", padx=(14, 0), pady=(6, 0))

        ctk.CTkButton(bar, text="Ayarlar", width=110, height=34, font=theme.font(13, "bold"),
                      fg_color=theme.NEUTRAL_BTN, hover_color=theme.NEUTRAL_BTN_HOVER,
                      text_color=("gray10", "gray90"),
                      command=self.open_settings).pack(side="right")
        ctk.CTkButton(bar, text="İstatistikler", width=130, height=34,
                      font=theme.font(13, "bold"),
                      command=self.open_stats).pack(side="right", padx=(0, 8))

    # ------------------------------------------------------------ pencereler
    def open_stats(self) -> None:
        if self._stats_win is not None and self._stats_win.winfo_exists():
            self._stats_win.render()
            self._stats_win.lift()
            self._stats_win.focus_force()
            return
        self._stats_win = StatsWindow(self, self.db)

    def open_settings(self) -> None:
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        self._settings_win = SettingsWindow(self, self.db, on_save=self._on_settings_saved)

    def _on_settings_saved(self) -> None:
        self.timer_panel.apply_settings()
        self.task_panel.refresh()
        if self._stats_win is not None and self._stats_win.winfo_exists():
            self._stats_win.render()

    # ------------------------------------------------------------ yardımcılar
    def _set_title_status(self, status: str | None) -> None:
        title = f"{status} — {APP_TITLE}" if status else APP_TITLE
        if title != self._last_title:  # her tikte gereksiz yere başlık değiştirme
            self._last_title = title
            self.title(title)

    def _check_day_change(self) -> None:
        """Gece yarısı geçtiyse tarih, son tarih uyarıları ve günlük toplamlar yenilenir."""
        if date.today() != self._today:
            self._today = date.today()
            self.date_label.configure(text=format_long_date(self._today, with_day=True))
            self.task_panel.refresh()
            self.timer_panel.refresh_stats()
        self.after(60_000, self._check_day_change)

    def _on_close(self) -> None:
        self.timer_panel.shutdown()  # süren çalışma oturumu kaydedilir
        if self._stats_win is not None and self._stats_win.winfo_exists():
            self._stats_win.close()
        self.db.close()
        self.destroy()
