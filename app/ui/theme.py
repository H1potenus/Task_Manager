"""Renkler, yazı tipleri ve tema ayarı."""
from __future__ import annotations

import sys

import customtkinter as ctk

# Segoe UI Windows'ta Türkçe karakterleri (ç ğ ı İ ö ş ü) eksiksiz destekler.
FONT_FAMILY = "Segoe UI" if sys.platform.startswith("win") else "Roboto"

# (açık mod, koyu mod) çiftleri
ACCENT = ("#2F7BD8", "#3B8ED0")
ACCENT_HOVER = ("#2766B4", "#36719F")
BREAK_COLOR = ("#1F8A5B", "#2FA572")
DANGER = ("#D93F44", "#C9373C")
DANGER_HOVER = ("#B3343A", "#A52D31")
WARNING_TEXT = ("#D12F35", "#FF6B6B")
MUTED_TEXT = ("gray40", "gray62")
DONE_TEXT = ("gray55", "gray45")
CARD = ("gray88", "gray17")
ROW = ("gray93", "gray21")
ROW_DONE = ("gray90", "gray18")
NEUTRAL_BTN = ("gray75", "gray28")
NEUTRAL_BTN_HOVER = ("gray68", "gray34")

APPEARANCE_MODES = {"dark": "Koyu", "light": "Açık", "system": "Sistem"}


def apply_theme(appearance: str = "dark") -> None:
    ctk.set_appearance_mode(appearance if appearance in APPEARANCE_MODES else "dark")
    ctk.set_default_color_theme("blue")
    ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY


def font(size: int = 13, weight: str = "normal", overstrike: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, overstrike=overstrike)
