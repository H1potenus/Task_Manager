"""Türkçe metin, tarih ve süre yardımcıları.

Python'un varsayılan lower()/sort() davranışı Türkçe için hatalıdır
("I".lower() -> "i", "İ".lower() -> "i̇", "Ç" ise "Z"den sonra sıralanır).
Bu modül bu sorunları düzeltir.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
TR_DAYS_SHORT = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

_TR_ALPHABET = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_TR_ORDER = {ch: i for i, ch in enumerate(_TR_ALPHABET)}


# --------------------------------------------------------------------- metin
def tr_lower(text: str) -> str:
    """Türkçe kurallarına uygun küçük harfe çevirme (I -> ı, İ -> i)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def tr_upper(text: str) -> str:
    """Türkçe kurallarına uygun büyük harfe çevirme (i -> İ, ı -> I)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def tr_sort_key(text: str) -> list[tuple[int, int]]:
    """Türk alfabesine göre sıralama anahtarı (a, b, c, ç, d, ... ğ ... ı, i ...)."""
    key = []
    for ch in tr_lower(text):
        if ch in _TR_ORDER:
            key.append((1, _TR_ORDER[ch]))
        else:  # rakamlar, boşluk ve işaretler harflerden önce gelir
            key.append((0, ord(ch)))
    return key


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------- süre
def format_duration(seconds: float) -> str:
    """3725 -> '1 sa 2 dk', 300 -> '5 dk', 42 -> '42 sn'."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} sn"
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours} sa {minutes} dk"
    if hours:
        return f"{hours} sa"
    return f"{minutes} dk"


def format_clock(seconds: float) -> str:
    """Sayaç görünümü: 'MM:SS' veya 'S:MM:SS'."""
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# --------------------------------------------------------------------- tarih
_DATE_FORMATS = ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%y"]


def parse_date(text: str) -> date | None:
    """Kullanıcının yazdığı tarihi çözer. Boş metin -> None.

    Kabul edilen biçimler: 15.10.2026, 15/10/2026, 15-10-2026, 2026-10-15,
    15.10.26 ve 'bugün', 'yarın' kelimeleri.
    Geçersiz girişte Türkçe mesajlı ValueError fırlatır.
    """
    from datetime import datetime

    text = text.strip()
    if not text:
        return None
    word = tr_lower(text)
    if word in ("bugün", "bugun"):
        return date.today()
    if word in ("yarın", "yarin"):
        return date.today() + timedelta(days=1)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"“{text}” geçerli bir tarih değil.\n"
        "Lütfen GG.AA.YYYY biçiminde yazın (ör. 15.10.2026)."
    )


def format_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def format_long_date(d: date, with_day: bool = False) -> str:
    text = f"{d.day} {TR_MONTHS[d.month - 1]} {d.year}"
    if with_day:
        text += f", {TR_DAYS[d.weekday()]}"
    return text


def week_bounds(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def month_bounds(d: date) -> tuple[date, date]:
    last = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=1), d.replace(day=last)


def add_months(d: date, delta: int) -> date:
    month_index = d.year * 12 + (d.month - 1) + delta
    year, month = divmod(month_index, 12)
    day = min(d.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day)
