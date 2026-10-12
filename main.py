"""Verimlilik Merkezi — giriş noktası.

Çalıştırma:  python main.py
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from app.database import Database
from app.ui import theme
from app.ui.main_window import MainWindow

DB_PATH = Path(__file__).resolve().parent / "veriler" / "verimlilik.db"


def main() -> None:
    if sys.platform.startswith("win"):
        try:  # Görev çubuğunda Python yerine uygulamanın kendi simgesi/grubu
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VerimlilikMerkezi")
        except (AttributeError, OSError):
            pass

    db = Database(DB_PATH)
    theme.apply_theme(db.get_setting("appearance_mode"))
    app = MainWindow(db)
    app.mainloop()


if __name__ == "__main__":
    main()
