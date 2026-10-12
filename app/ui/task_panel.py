"""Sol panel: görevler ve alt görevler."""
from __future__ import annotations

from datetime import date
from typing import Callable

import customtkinter as ctk

from ..database import Database, Task
from ..utils import format_date, parse_date
from . import theme
from .dialogs import ask_text, ask_yes_no, show_message


class TaskPanel(ctk.CTkFrame):
    def __init__(self, master, db: Database, get_warning_days: Callable[[], int]):
        super().__init__(master, fg_color=theme.CARD, corner_radius=12)
        self.db = db
        self.get_warning_days = get_warning_days

        # Satırlar her yenilemede yeniden çizildiği için yazı tipleri bir kez oluşturulur.
        self.f_title = theme.font(20, "bold")
        self.f_main = theme.font(14, "bold")
        self.f_main_done = theme.font(14, "bold", overstrike=True)
        self.f_sub = theme.font(13)
        self.f_sub_done = theme.font(13, overstrike=True)
        self.f_small = theme.font(11)
        self.f_section = theme.font(12, "bold")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text="Görevler", font=self.f_title).pack(side="left")
        self.counter_label = ctk.CTkLabel(header, text="", font=self.f_small,
                                          text_color=theme.MUTED_TEXT)
        self.counter_label.pack(side="right")

        add_bar = ctk.CTkFrame(self, fg_color="transparent")
        add_bar.grid(row=1, column=0, sticky="ew", padx=16)
        add_bar.grid_columnconfigure(0, weight=1)
        self.title_entry = ctk.CTkEntry(add_bar, height=36,
                                        placeholder_text="Yeni görev / proje adı…")
        self.title_entry.grid(row=0, column=0, sticky="ew")
        self.deadline_entry = ctk.CTkEntry(add_bar, width=190, height=36,
                                           placeholder_text="Son tarih (GG.AA.YYYY)")
        self.deadline_entry.grid(row=0, column=1, padx=8)
        ctk.CTkButton(add_bar, text="+ Ekle", width=90, height=36, font=theme.font(13, "bold"),
                      command=self._add_task).grid(row=0, column=2)
        self.title_entry.bind("<Return>", self._add_task)
        self.deadline_entry.bind("<Return>", self._add_task)

        ctk.CTkLabel(
            self, font=self.f_small, text_color=theme.MUTED_TEXT, anchor="w",
            text="İpucu: Görevin adına tıklayınca tamamlandı olarak işaretlenir; "
                 "tekrar tıklayınca geri alınır. Son tarih isteğe bağlıdır.",
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(6, 4))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 12))

        self.refresh()

    # ------------------------------------------------------------ eylemler
    def _add_task(self, _event=None) -> None:
        title = self.title_entry.get().strip()
        if not title:
            self.title_entry.focus_set()
            return
        try:
            deadline = parse_date(self.deadline_entry.get())
        except ValueError as exc:
            show_message(self, "Geçersiz tarih", str(exc))
            return
        self.db.add_task(title, None, deadline)
        self.title_entry.delete(0, "end")
        self.deadline_entry.delete(0, "end")
        self.focus_set()  # placeholder'ların geri gelmesi için odak entry'den çıkar
        self.refresh()

    def _toggle(self, task: Task) -> None:
        self.db.set_task_done(task.id, not task.is_done)
        # Satırı kendi tıklama olayının içinde yok etmemek için bir sonraki boş anda yenile.
        self.after_idle(self.refresh)

    def _add_subtask(self, parent: Task) -> None:
        title = ask_text(self, "Alt Görev Ekle", f"“{parent.title}” görevine alt görev ekleyin:",
                         placeholder="Alt görev adı…")
        if title and title.strip():
            self.db.add_task(title, parent.id)
            self.refresh()

    def _edit_deadline(self, task: Task) -> None:
        text = ask_text(
            self, "Son Tarih",
            f"“{task.title}” için son tarih (GG.AA.YYYY).\nKaldırmak için boş bırakın.",
            initial=format_date(task.deadline) if task.deadline else "",
            placeholder="ör. 15.10.2026",
        )
        if text is None:
            return
        try:
            deadline = parse_date(text)
        except ValueError as exc:
            show_message(self, "Geçersiz tarih", str(exc))
            return
        self.db.set_deadline(task.id, deadline)
        self.refresh()

    def _delete(self, task: Task) -> None:
        if task.subtasks:
            msg = (f"“{task.title}” ve {len(task.subtasks)} alt görevi silinecek.\n"
                   "Bu işlem geri alınamaz. Emin misiniz?")
            if not ask_yes_no(self, "Görevi Sil", msg, ok_text="Sil"):
                return
        self.db.delete_task(task.id)
        self.refresh()

    # ------------------------------------------------------------ çizim
    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()

        tasks = self.db.get_task_tree()
        done_count = sum(t.is_done for t in tasks)
        self.counter_label.configure(text=f"{done_count} / {len(tasks)} görev tamamlandı")

        if not tasks:
            ctk.CTkLabel(self.list_frame, text="Henüz görev yok. Yukarıdan ilk görevini ekle!",
                         font=self.f_sub, text_color=theme.MUTED_TEXT).pack(pady=40)
            return

        done_header_shown = False
        for task in tasks:
            if task.is_done and not done_header_shown:
                done_header_shown = True
                ctk.CTkLabel(self.list_frame, text="TAMAMLANANLAR", font=self.f_section,
                             text_color=theme.MUTED_TEXT, anchor="w").pack(
                    fill="x", padx=10, pady=(16, 0))
            self._build_main_row(task)
            for sub in task.subtasks:
                self._build_sub_row(sub)

    def _deadline_info(self, task: Task) -> tuple[str, bool]:
        """(gösterilecek metin, uyarı mı?)"""
        if not task.deadline:
            return "", False
        ds = format_date(task.deadline)
        if task.is_done:
            return f"Son: {ds}", False
        days = (task.deadline - date.today()).days
        if days < 0:
            return f"{ds} · {-days} gün gecikti", True
        if days == 0:
            return f"{ds} · Bugün son gün", True
        return f"{ds} · {days} gün kaldı", days <= self.get_warning_days()

    def _small_button(self, parent, text: str, command, danger: bool = False,
                      state: str = "normal") -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, width=10, height=26, font=self.f_small,
            state=state,
            fg_color=theme.DANGER if danger else theme.NEUTRAL_BTN,
            hover_color=theme.DANGER_HOVER if danger else theme.NEUTRAL_BTN_HOVER,
            text_color=("white" if danger else ("gray10", "gray90")),
        )

    def _build_main_row(self, task: Task) -> None:
        row = ctk.CTkFrame(self.list_frame, corner_radius=8,
                           fg_color=theme.ROW_DONE if task.is_done else theme.ROW)
        row.pack(fill="x", padx=4, pady=(8, 2))
        row.grid_columnconfigure(1, weight=1)

        cb = ctk.CTkCheckBox(row, text="", width=24, checkbox_width=20, checkbox_height=20,
                             command=lambda t=task: self._toggle(t))
        if task.is_done:
            cb.select()
        cb.grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=10)

        info, warn = self._deadline_info(task)
        if task.is_done:
            color = theme.DONE_TEXT
        elif warn:
            color = theme.WARNING_TEXT
        else:
            color = ("gray10", "gray92")

        label = ctk.CTkLabel(row, text=("! " if warn else "") + task.title, anchor="w",
                             justify="left", wraplength=420, cursor="hand2", text_color=color,
                             font=self.f_main_done if task.is_done else self.f_main)
        label.grid(row=0, column=1, sticky="ew", pady=(8, 0) if info else 8)
        label.bind("<Button-1>", lambda _e, t=task: self._toggle(t))

        if info:
            ctk.CTkLabel(row, text=info, font=self.f_small, anchor="w", height=16,
                         text_color=theme.WARNING_TEXT if warn else theme.MUTED_TEXT).grid(
                row=1, column=1, sticky="ew", pady=(0, 8))

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=2, padx=8)
        state = "disabled" if task.is_done else "normal"
        self._small_button(btns, "+ Alt görev", lambda t=task: self._add_subtask(t),
                           state=state).pack(side="left", padx=2)
        self._small_button(btns, "Tarih", lambda t=task: self._edit_deadline(t),
                           state=state).pack(side="left", padx=2)
        self._small_button(btns, "Sil", lambda t=task: self._delete(t),
                           danger=True).pack(side="left", padx=2)

    def _build_sub_row(self, task: Task) -> None:
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", padx=(34, 4), pady=1)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(row, text="└", text_color=theme.MUTED_TEXT, width=14).grid(
            row=0, column=0, padx=(0, 4))
        cb = ctk.CTkCheckBox(row, text="", width=22, checkbox_width=18, checkbox_height=18,
                             command=lambda t=task: self._toggle(t))
        if task.is_done:
            cb.select()
        cb.grid(row=0, column=1, padx=(0, 4))

        label = ctk.CTkLabel(row, text=task.title, anchor="w", justify="left", wraplength=400,
                             cursor="hand2",
                             text_color=theme.DONE_TEXT if task.is_done else ("gray15", "gray85"),
                             font=self.f_sub_done if task.is_done else self.f_sub)
        label.grid(row=0, column=2, sticky="ew")
        label.bind("<Button-1>", lambda _e, t=task: self._toggle(t))

        self._small_button(row, "Sil", lambda t=task: self._delete(t), danger=True).grid(
            row=0, column=3, padx=(4, 8))
