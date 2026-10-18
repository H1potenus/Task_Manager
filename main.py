"""Task Planner / Pomodoro Timer — giriş noktası.

Çalıştırma:  python main.py
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from app.database import Database
from app.ui import theme
from app.ui.main_window import MainWindow

# Exe olarak çalışırken veriler, exe'nin yanındaki "veriler" klasöründe tutulur.
# (Klasör/dosya adı, eski sürümlerden gelen verilerin korunması için bilerek değiştirilmedi.)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "veriler" / "verimlilik.db"


def main() -> None:
    if sys.platform.startswith("win"):
        try:  # Görev çubuğunda Python yerine uygulamanın kendi simgesi/grubu
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("H1potenus.TaskPlannerPomodoroTimer")
        except (AttributeError, OSError):
            pass

    db = Database(DB_PATH)
    theme.apply_theme(db.get_setting("appearance_mode"))
    app = MainWindow(db)
    app.mainloop()


if __name__ == "__main__":
    main()
