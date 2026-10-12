"""Ayarlar penceresi: Pomodoro süreleri, son tarih uyarısı, ses ve görünüm."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..database import Database
from ..sound import play_melody
from . import theme

# ayar anahtarı, etiket, en az, en çok
NUMERIC_FIELDS = [
    ("work_minutes", "Pomodoro çalışma süresi (dakika)", 1, 240),
    ("break_minutes", "Pomodoro mola süresi (dakika)", 1, 120),
    ("deadline_warning_days", "Son tarih uyarısı (kaç gün kala)", 0, 60),
]


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, db: Database, on_save: Callable[[], None]):
        super().__init__(master)
        self.db = db
        self.on_save = on_save
        self.title("Ayarlar")
        self.resizable(False, False)
        self.transient(master)

        ctk.CTkLabel(self, text="Ayarlar", font=theme.font(20, "bold")).pack(
            anchor="w", padx=24, pady=(18, 10))

        form = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=10)
        form.pack(fill="x", padx=20)
        form.grid_columnconfigure(0, weight=1)

        self.entries: dict[str, ctk.CTkEntry] = {}
        for row, (key, label, lo, hi) in enumerate(NUMERIC_FIELDS):
            ctk.CTkLabel(form, text=label, anchor="w").grid(
                row=row, column=0, sticky="w", padx=16, pady=8)
            entry = ctk.CTkEntry(form, width=80, justify="center")
            entry.insert(0, db.get_setting(key))
            entry.grid(row=row, column=1, padx=16, pady=8)
            self.entries[key] = entry

        row = len(NUMERIC_FIELDS)
        ctk.CTkLabel(form, text="Süre bitince melodi çal", anchor="w").grid(
            row=row, column=0, sticky="w", padx=16, pady=8)
        sound_box = ctk.CTkFrame(form, fg_color="transparent")
        sound_box.grid(row=row, column=1, padx=16, pady=8)
        self.sound_switch = ctk.CTkSwitch(sound_box, text="", width=46)
        if db.get_setting("sound_enabled") == "1":
            self.sound_switch.select()
        self.sound_switch.pack(side="left")
        ctk.CTkButton(sound_box, text="Dene", width=50, height=26,
                      command=lambda: play_melody("work_finished", fallback=self.bell)).pack(
            side="left", padx=(4, 0))

        ctk.CTkLabel(form, text="Görünüm", anchor="w").grid(
            row=row + 1, column=0, sticky="w", padx=16, pady=(8, 14))
        self._mode_by_label = {v: k for k, v in theme.APPEARANCE_MODES.items()}
        self.appearance = ctk.CTkOptionMenu(form, width=110,
                                            values=list(theme.APPEARANCE_MODES.values()))
        self.appearance.set(theme.APPEARANCE_MODES.get(db.get_setting("appearance_mode"), "Koyu"))
        self.appearance.grid(row=row + 1, column=1, padx=16, pady=(8, 14))

        ctk.CTkLabel(self, text="Not: Çalışan bir oturum varsa yeni süreler bir sonraki "
                                "fazdan itibaren geçerli olur.",
                     font=theme.font(11), text_color=theme.MUTED_TEXT, wraplength=400,
                     justify="left").pack(anchor="w", padx=24, pady=(8, 0))
        self.error_label = ctk.CTkLabel(self, text="", text_color=theme.WARNING_TEXT,
                                        wraplength=400, justify="left")
        self.error_label.pack(anchor="w", padx=24)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(4, 18))
        ctk.CTkButton(bar, text="Kaydet", width=110, command=self._save).pack(side="right")
        ctk.CTkButton(bar, text="İptal", width=110, fg_color=theme.NEUTRAL_BTN,
                      hover_color=theme.NEUTRAL_BTN_HOVER, text_color=("gray10", "gray90"),
                      command=self.destroy).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(150, self._bring_front)

    def _bring_front(self) -> None:
        self.lift()
        self.focus_force()

    def _save(self) -> None:
        values: dict[str, str] = {}
        for key, label, lo, hi in NUMERIC_FIELDS:
            text = self.entries[key].get().strip()
            try:
                number = int(text)
            except ValueError:
                number = None
            if number is None or not lo <= number <= hi:
                self.error_label.configure(
                    text=f"“{label}” için {lo} ile {hi} arasında bir tam sayı girin.")
                self.entries[key].focus_set()
                return
            values[key] = str(number)
        values["sound_enabled"] = "1" if self.sound_switch.get() else "0"
        mode = self._mode_by_label[self.appearance.get()]
        values["appearance_mode"] = mode

        self.db.set_settings(values)
        ctk.set_appearance_mode(mode)
        self.on_save()
        self.destroy()
