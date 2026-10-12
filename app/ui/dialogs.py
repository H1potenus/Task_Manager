"""Türkçe butonlu modal pencereler.

customtkinter'ın CTkInputDialog'u ve tkinter.messagebox butonları
("Ok", "Cancel", "Yes", "No") sistem diline göre İngilizce çıkabildiği için
kendi diyaloglarımızı kullanıyoruz.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from . import theme


class _BaseDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.result = None
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())

    def _show(self):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.after(60, self._grab)
        self.wait_window()
        return self.result

    def _grab(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
            self._focus_first()
        except tk.TclError:
            pass

    def _focus_first(self) -> None:
        pass

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _buttons(self, ok_text: str, cancel_text: str | None, danger: bool = False) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(4, 18))
        ok = ctk.CTkButton(
            bar, text=ok_text, width=110, command=self._ok,
            fg_color=theme.DANGER if danger else theme.ACCENT,
            hover_color=theme.DANGER_HOVER if danger else theme.ACCENT_HOVER,
        )
        ok.pack(side="right")
        if cancel_text:
            ctk.CTkButton(
                bar, text=cancel_text, width=110, command=self._cancel,
                fg_color=theme.NEUTRAL_BTN, hover_color=theme.NEUTRAL_BTN_HOVER,
                text_color=("gray10", "gray90"),
            ).pack(side="right", padx=(0, 8))

    def _ok(self) -> None:
        self.destroy()


class TextInputDialog(_BaseDialog):
    def __init__(self, master, title: str, prompt: str, initial: str = "", placeholder: str = ""):
        super().__init__(master, title)
        ctk.CTkLabel(self, text=prompt, font=theme.font(13), justify="left",
                     wraplength=360, anchor="w").pack(fill="x", padx=20, pady=(18, 8))
        self.entry = ctk.CTkEntry(self, width=360, placeholder_text=placeholder)
        self.entry.pack(padx=20, pady=(0, 14))
        if initial:
            self.entry.insert(0, initial)
        self.entry.bind("<Return>", lambda _e: self._ok())
        self._buttons("Tamam", "İptal")

    def _focus_first(self) -> None:
        self.entry.focus_set()

    def _ok(self) -> None:
        self.result = self.entry.get()
        self.destroy()


class ConfirmDialog(_BaseDialog):
    def __init__(self, master, title: str, message: str, ok_text: str, danger: bool):
        super().__init__(master, title)
        ctk.CTkLabel(self, text=message, font=theme.font(13), justify="left",
                     wraplength=380, anchor="w").pack(fill="x", padx=20, pady=(20, 14))
        self.result = False
        self._buttons(ok_text, "Vazgeç", danger=danger)

    def _ok(self) -> None:
        self.result = True
        self.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.destroy()


class MessageDialog(_BaseDialog):
    def __init__(self, master, title: str, message: str):
        super().__init__(master, title)
        ctk.CTkLabel(self, text=message, font=theme.font(13), justify="left",
                     wraplength=380, anchor="w").pack(fill="x", padx=20, pady=(20, 14))
        self._buttons("Tamam", None)
        self.bind("<Return>", lambda _e: self._ok())


def ask_text(master, title: str, prompt: str, initial: str = "", placeholder: str = "") -> str | None:
    return TextInputDialog(master, title, prompt, initial, placeholder)._show()


def ask_yes_no(master, title: str, message: str, ok_text: str = "Evet", danger: bool = True) -> bool:
    return bool(ConfirmDialog(master, title, message, ok_text, danger)._show())


def show_message(master, title: str, message: str) -> None:
    MessageDialog(master, title, message)._show()
