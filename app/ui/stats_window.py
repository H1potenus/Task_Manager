"""İstatistik penceresi: günlük / haftalık / aylık çalışma grafikleri (matplotlib)."""
from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ..database import Database  # noqa: E402
from ..utils import (TR_DAYS_SHORT, TR_MONTHS, add_months, format_duration,  # noqa: E402
                     format_long_date, month_bounds, shorten, week_bounds)
from . import theme  # noqa: E402

matplotlib.rcParams["font.family"] = [theme.FONT_FAMILY, "DejaVu Sans"]

PERIODS = ("Günlük", "Haftalık", "Aylık")

# Tek seri = tek renk. Metinler seri rengini değil, metin renklerini kullanır.
PALETTES = {
    "dark": {"bg": "#242424", "text": "#DCE4EE", "muted": "#9AA3AD", "grid": "#3A3A3A",
             "bar": "#3B8ED0", "today": "#7DB8EA"},
    "light": {"bg": "#EBEBEB", "text": "#1F1F1F", "muted": "#5C5C5C", "grid": "#D0D0D0",
              "bar": "#2F7BD8", "today": "#1D4F8C"},
}


class StatsWindow(ctk.CTkToplevel):
    def __init__(self, master, db: Database):
        super().__init__(master)
        self.db = db
        self.title("İstatistikler")
        self.geometry("900x620")
        self.minsize(700, 500)
        self._period = PERIODS[0]
        self._anchor = date.today()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 6))
        self.period_switch = ctk.CTkSegmentedButton(top, values=list(PERIODS), height=34,
                                                    font=theme.font(13, "bold"),
                                                    command=self._on_period)
        self.period_switch.set(self._period)
        self.period_switch.pack(side="left")

        nav = ctk.CTkFrame(top, fg_color="transparent")
        nav.pack(side="right")
        ctk.CTkButton(nav, text="◀", width=36, height=32,
                      command=lambda: self._shift(-1)).pack(side="left")
        self.range_label = ctk.CTkLabel(nav, text="", width=230, font=theme.font(14, "bold"))
        self.range_label.pack(side="left", padx=6)
        self.next_btn = ctk.CTkButton(nav, text="▶", width=36, height=32,
                                      command=lambda: self._shift(1))
        self.next_btn.pack(side="left")
        ctk.CTkButton(nav, text="Bugün", width=70, height=32, fg_color=theme.NEUTRAL_BTN,
                      hover_color=theme.NEUTRAL_BTN_HOVER, text_color=("gray10", "gray90"),
                      command=self._go_today).pack(side="left", padx=(8, 0))

        self.summary_label = ctk.CTkLabel(self, text="", font=theme.font(14), anchor="w")
        self.summary_label.pack(fill="x", padx=22, pady=(4, 0))

        self.figure = Figure(figsize=(8.6, 5.4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=14, pady=(6, 14))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.render()
        self.after(150, self._bring_front)

    def _bring_front(self) -> None:
        self.lift()
        self.focus_force()

    def close(self) -> None:
        self.figure.clear()
        self.destroy()

    # ------------------------------------------------------------ gezinme
    def _on_period(self, value: str) -> None:
        self._period = value
        self.render()

    def _go_today(self) -> None:
        self._anchor = date.today()
        self.render()

    def _shift(self, step: int) -> None:
        if self._period == "Günlük":
            self._anchor += timedelta(days=step)
        elif self._period == "Haftalık":
            self._anchor += timedelta(days=7 * step)
        else:
            self._anchor = add_months(self._anchor, step)
        self.render()

    def _range(self) -> tuple[date, date, str]:
        a = self._anchor
        if self._period == "Günlük":
            return a, a, format_long_date(a, with_day=True)
        if self._period == "Haftalık":
            start, end = week_bounds(a)
            if start.month == end.month:
                label = f"{start.day} – {end.day} {TR_MONTHS[end.month - 1]} {end.year}"
            elif start.year == end.year:
                label = (f"{start.day} {TR_MONTHS[start.month - 1]} – "
                         f"{end.day} {TR_MONTHS[end.month - 1]} {end.year}")
            else:
                label = f"{format_long_date(start)} – {format_long_date(end)}"
            return start, end, label
        start, end = month_bounds(a)
        return start, end, f"{TR_MONTHS[a.month - 1]} {a.year}"

    # ------------------------------------------------------------ çizim
    def render(self) -> None:
        start, end, label = self._range()
        today = date.today()
        self.range_label.configure(text=label)
        self.next_btn.configure(state="disabled" if end >= today else "normal")

        cat_totals = self.db.get_category_totals(start, end)
        total = sum(s for _, s in cat_totals)
        summary = f"Toplam çalışma: {format_duration(total)}"
        if self._period != "Günlük" and total:
            days_so_far = (min(end, today) - start).days + 1
            if days_so_far > 0:
                summary += f"   ·   Günlük ortalama: {format_duration(total / days_so_far)}"
        self.summary_label.configure(text=summary)

        mode = "light" if ctk.get_appearance_mode() == "Light" else "dark"
        pal = PALETTES[mode]
        fig = self.figure
        fig.clear()
        fig.set_facecolor(pal["bg"])

        if not cat_totals:
            ax = fig.add_subplot(111)
            self._style(ax, pal)
            ax.axis("off")
            ax.text(0.5, 0.5, "Bu dönemde kayıtlı çalışma yok.", ha="center", va="center",
                    fontsize=14, color=pal["muted"], transform=ax.transAxes)
        elif self._period == "Günlük":
            ax = fig.add_subplot(111)
            self._draw_category_bars(ax, cat_totals, pal, "Kategori başına çalışma (saat)")
        else:
            gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.55)
            ax1 = fig.add_subplot(gs[0])
            self._draw_category_bars(ax1, cat_totals, pal, "Kategori başına çalışma (saat)")
            ax2 = fig.add_subplot(gs[1])
            self._draw_daily_bars(ax2, self.db.get_daily_totals(start, end), pal, today)

        fig.subplots_adjust(left=0.24, right=0.95, top=0.92, bottom=0.10)
        self.canvas.draw_idle()

    @staticmethod
    def _style(ax, pal) -> None:
        ax.set_facecolor(pal["bg"])
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(pal["grid"])
        ax.tick_params(colors=pal["muted"], labelsize=10, length=0)
        ax.set_axisbelow(True)

    def _draw_category_bars(self, ax, totals, pal, title: str) -> None:
        self._style(ax, pal)
        totals = list(reversed(totals))  # en büyük en üstte
        names = [shorten(n, 26) for n, _ in totals]
        hours = [s / 3600 for _, s in totals]
        bars = ax.barh(names, hours, color=pal["bar"], height=0.55)
        ax.tick_params(axis="y", labelcolor=pal["text"], labelsize=11)
        ax.grid(axis="x", color=pal["grid"], linewidth=0.8)
        ax.set_title(title, color=pal["text"], fontsize=12, loc="left", pad=10)
        peak = max(hours)
        ax.set_xlim(0, peak * 1.25 if peak else 1)
        for bar, (_, secs) in zip(bars, totals):
            ax.text(bar.get_width() + peak * 0.015, bar.get_y() + bar.get_height() / 2,
                    format_duration(secs), va="center", fontsize=10, color=pal["text"])

    def _draw_daily_bars(self, ax, daily, pal, today: date) -> None:
        self._style(ax, pal)
        weekly = self._period == "Haftalık"
        labels = [f"{TR_DAYS_SHORT[d.weekday()]}\n{d.day:02d}.{d.month:02d}" if weekly
                  else str(d.day) for d, _ in daily]
        hours = [s / 3600 for _, s in daily]
        colors = [pal["today"] if d == today else pal["bar"] for d, _ in daily]
        ax.bar(range(len(daily)), hours, color=colors, width=0.6 if weekly else 0.7)
        ax.set_xticks(range(len(daily)), labels, fontsize=10 if weekly else 8)
        ax.grid(axis="y", color=pal["grid"], linewidth=0.8)
        ax.set_ylabel("Saat", color=pal["muted"])
        ax.set_title("Günlere göre toplam çalışma", color=pal["text"], fontsize=12,
                     loc="left", pad=10)
        if max(hours) == 0:
            ax.set_ylim(0, 1)
