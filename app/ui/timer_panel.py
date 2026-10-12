"""Sağ panel: kategoriler ve zamanlayıcı (Süreölçer / Pomodoro)."""
from __future__ import annotations

from datetime import date
from typing import Callable

import customtkinter as ctk

from ..database import Category, Database
from ..sound import play_melody
from ..timer_logic import Phase, TimerEngine, TimerMode, TimerState
from ..utils import format_clock, format_duration
from . import theme
from .dialogs import ask_yes_no, show_message

MODE_LABELS = {TimerMode.STOPWATCH: "Süreölçer", TimerMode.POMODORO: "Pomodoro"}
TICK_MS = 200


class TimerPanel(ctk.CTkFrame):
    def __init__(self, master, db: Database, on_title_change: Callable[[str | None], None]):
        super().__init__(master, fg_color=theme.CARD, corner_radius=12)
        self.db = db
        self.on_title_change = on_title_change
        self.engine = TimerEngine(db.get_int_setting("work_minutes"),
                                  db.get_int_setting("break_minutes"))
        self._categories: dict[str, Category] = {}
        self._session_category: Category | None = None
        self._after_id: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self._build_category_section()
        self._build_timer_section()

        self._reload_categories()
        self._update_controls()
        self._loop()

    # ================================================================ arayüz
    def _build_category_section(self) -> None:
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(box, text="Kategori", font=theme.font(20, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(box, text="Süre, seçili kategoriye kaydedilir.", font=theme.font(11),
                     text_color=theme.MUTED_TEXT, anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.category_box = ctk.CTkComboBox(box, values=[], state="readonly", height=36,
                                            command=lambda _v: self._update_today_label())
        self.category_box.grid(row=2, column=0, sticky="ew")
        self.delete_cat_btn = ctk.CTkButton(
            box, text="Sil", width=60, height=36, command=self._delete_category,
            fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER)
        self.delete_cat_btn.grid(row=2, column=1, padx=(8, 0))

        self.new_cat_entry = ctk.CTkEntry(box, height=34, placeholder_text="Yeni kategori adı…")
        self.new_cat_entry.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.new_cat_entry.bind("<Return>", lambda _e: self._add_category())
        ctk.CTkButton(box, text="Ekle", width=60, height=34, command=self._add_category).grid(
            row=3, column=1, padx=(8, 0), pady=(8, 0))

    def _build_timer_section(self) -> None:
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(14, 16))
        box.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.mode_switch = ctk.CTkSegmentedButton(
            box, values=list(MODE_LABELS.values()), height=34, font=theme.font(13, "bold"),
            command=self._on_mode_change)
        self.mode_switch.set(MODE_LABELS[self.engine.mode])
        self.mode_switch.grid(row=0, column=0, sticky="ew")

        self.phase_label = ctk.CTkLabel(box, text="", font=theme.font(16, "bold"))
        self.phase_label.grid(row=1, column=0, pady=(22, 0))

        self.time_label = ctk.CTkLabel(box, text="00:00", font=theme.font(76, "bold"))
        self.time_label.grid(row=2, column=0, pady=(0, 4))

        self.progress = ctk.CTkProgressBar(box, height=8)
        self.progress.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 20))

        self.main_btn = ctk.CTkButton(box, text="Başlat", height=64, corner_radius=14,
                                      font=theme.font(22, "bold"), command=self._on_primary)
        self.main_btn.grid(row=4, column=0, sticky="ew")

        self.finish_btn = ctk.CTkButton(
            box, text="Bitir ve Kaydet", height=34, font=theme.font(13),
            fg_color="transparent", border_width=1, border_color=theme.NEUTRAL_BTN,
            hover_color=theme.NEUTRAL_BTN, text_color=("gray10", "gray90"),
            command=self._on_finish)
        self.finish_btn.grid(row=5, column=0, sticky="ew", pady=(8, 0))

        self.status_label = ctk.CTkLabel(box, text="", font=theme.font(12),
                                         text_color=theme.MUTED_TEXT, wraplength=340)
        self.status_label.grid(row=6, column=0, pady=(12, 0))

        stats = ctk.CTkFrame(box, fg_color=theme.ROW, corner_radius=10)
        stats.grid(row=7, column=0, sticky="ew", pady=(16, 0))
        self.today_cat_label = ctk.CTkLabel(stats, text="", font=theme.font(13), anchor="w")
        self.today_cat_label.pack(fill="x", padx=14, pady=(10, 0))
        self.today_all_label = ctk.CTkLabel(stats, text="", font=theme.font(12), anchor="w",
                                            text_color=theme.MUTED_TEXT)
        self.today_all_label.pack(fill="x", padx=14, pady=(0, 10))

    # ============================================================ kategoriler
    def _reload_categories(self, select: str | None = None) -> None:
        cats = self.db.get_categories()
        self._categories = {c.name: c for c in cats}
        names = list(self._categories)
        current = select or self.category_box.get()
        self.category_box.configure(values=names)
        if current in self._categories:
            self.category_box.set(current)
        elif names:
            self.category_box.set(names[0])
        else:
            self.category_box.set("")
        self._update_today_label()

    def _selected_category(self) -> Category | None:
        return self._categories.get(self.category_box.get())

    def _add_category(self) -> None:
        name = self.new_cat_entry.get()
        try:
            cat = self.db.add_category(name)
        except ValueError as exc:
            show_message(self, "Kategori eklenemedi", str(exc))
            return
        self.new_cat_entry.delete(0, "end")
        self.focus_set()
        if self.engine.is_active and self._session_category:
            self._reload_categories(select=self._session_category.name)
        else:
            self._reload_categories(select=cat.name)
        self.status_label.configure(text=f"“{cat.name}” kategorisi eklendi.")

    def _delete_category(self) -> None:
        cat = self._selected_category()
        if cat is None:
            return
        if not ask_yes_no(self, "Kategoriyi Sil",
                          f"“{cat.name}” kategorisi ve bu kategoriye ait TÜM süre kayıtları "
                          "silinecek. Emin misiniz?", ok_text="Sil"):
            return
        self.db.delete_category(cat.id)
        self.category_box.set("")
        self._reload_categories()
        self.status_label.configure(text=f"“{cat.name}” kategorisi silindi.")

    # ============================================================ zamanlayıcı
    def _on_mode_change(self, label: str) -> None:
        mode = next(m for m, text in MODE_LABELS.items() if text == label)
        if self.engine.is_active:  # güvenlik: normalde buton devre dışıdır
            self.mode_switch.set(MODE_LABELS[self.engine.mode])
            return
        self.engine.set_mode(mode)
        self._update_controls()

    def _on_primary(self) -> None:
        if self.engine.state == TimerState.IDLE:
            cat = self._selected_category()
            if cat is None:
                show_message(self, "Kategori seçin",
                             "Zamanlayıcıyı başlatmadan önce bir kategori seçin veya ekleyin.")
                return
            self._session_category = cat
            self.status_label.configure(text="")
        self.engine.primary_action()
        self._update_controls()

    def _on_finish(self) -> None:
        was_break = self.engine.phase == Phase.BREAK
        seconds = self.engine.finish()
        if was_break:
            self.status_label.configure(text="Mola atlandı. Yeni pomodoroya hazırsın.")
        else:
            self._log(seconds)
        self._session_category = None
        self._update_controls()

    def _log(self, seconds: int) -> None:
        cat = self._session_category
        if cat is None:
            return
        if seconds < 1:
            self.status_label.configure(text="Süre çok kısa olduğu için kaydedilmedi.")
            return
        self.db.add_time_log(cat.id, seconds, date.today(), self.engine.mode.value)
        self.status_label.configure(text=f"✓ {format_duration(seconds)} → “{cat.name}” kaydedildi.")
        self._update_today_label()

    def _loop(self) -> None:
        event = self.engine.tick()
        if event is not None:
            self._handle_event(event.kind, event.seconds_to_log)
        self._refresh_display()
        self._after_id = self.after(TICK_MS, self._loop)

    def _handle_event(self, kind: str, seconds: int) -> None:
        sound_on = self.db.get_setting("sound_enabled") == "1"
        if kind == "work_finished":
            self._log(seconds)
            self.status_label.configure(
                text=self.status_label.cget("text") + "\nÇalışma bitti, mola başladı.")
        else:
            self.status_label.configure(text="Mola bitti! Yeni pomodoroya hazırsın.")
            self._session_category = None
        if sound_on:
            play_melody(kind, fallback=self.bell)
        self._update_controls()

    # ================================================================ görünüm
    def _refresh_display(self) -> None:
        e = self.engine
        self.time_label.configure(text=format_clock(e.display_seconds()))
        if e.mode == TimerMode.POMODORO:
            self.progress.set(e.progress())
        if e.is_active:
            phase = "Mola" if e.phase == Phase.BREAK else "Çalışma"
            self.on_title_change(f"{format_clock(e.display_seconds())} · {phase}")
        else:
            self.on_title_change(None)

    def _update_controls(self) -> None:
        e = self.engine
        active = e.is_active
        is_break = e.mode == TimerMode.POMODORO and e.phase == Phase.BREAK

        self.main_btn.configure(
            text={TimerState.IDLE: "Başlat", TimerState.RUNNING: "Duraklat",
                  TimerState.PAUSED: "Devam Et"}[e.state],
            fg_color=theme.BREAK_COLOR if is_break else theme.ACCENT,
            hover_color=theme.BREAK_COLOR if is_break else theme.ACCENT_HOVER,
        )
        if active:
            self.finish_btn.configure(text="Molayı Atla" if is_break else "Bitir ve Kaydet")
            self.finish_btn.grid()
        else:
            self.finish_btn.grid_remove()

        # Oturum sürerken kategori ve mod kilitlenir.
        lock = "disabled" if active else "normal"
        self.mode_switch.configure(state=lock)
        self.category_box.configure(state="disabled" if active else "readonly")
        self.delete_cat_btn.configure(state=lock)

        if e.mode == TimerMode.STOPWATCH:
            self.progress.grid_remove()
            phase_text, color = "Süreölçer", theme.ACCENT
        else:
            self.progress.grid()
            self.progress.configure(progress_color=theme.BREAK_COLOR if is_break else theme.ACCENT)
            if is_break:
                phase_text, color = f"Mola · {e.break_minutes} dk", theme.BREAK_COLOR
            else:
                phase_text, color = f"Çalışma · {e.work_minutes} dk", theme.ACCENT
        if e.state == TimerState.PAUSED:
            phase_text += "  (duraklatıldı)"
        if active and self._session_category:
            phase_text += f"\n{self._session_category.name}"
        self.phase_label.configure(text=phase_text, text_color=color)
        self._refresh_display()

    def _update_today_label(self) -> None:
        today = date.today()
        cat = self._selected_category()
        if cat:
            secs = self.db.get_seconds_on(today, cat.id)
            self.today_cat_label.configure(text=f"Bugün “{cat.name}”: {format_duration(secs)}")
        else:
            self.today_cat_label.configure(text="Kategori seçilmedi")
        total = self.db.get_seconds_on(today)
        self.today_all_label.configure(text=f"Bugün toplam: {format_duration(total)}")

    # ============================================================ dış arayüz
    def apply_settings(self) -> None:
        self.engine.set_durations(self.db.get_int_setting("work_minutes"),
                                  self.db.get_int_setting("break_minutes"))
        self._update_controls()

    def refresh_stats(self) -> None:
        self._update_today_label()

    def shutdown(self) -> None:
        """Uygulama kapanırken: süren çalışma oturumu varsa kaydet."""
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self.engine.is_active and self.engine.phase == Phase.WORK:
            self._log(self.engine.finish())
