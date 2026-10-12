"""SQLite veritabanı katmanı: Kategoriler, Görevler, Süre Kayıtları ve Ayarlar."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .utils import tr_lower, tr_sort_key

DEFAULT_SETTINGS = {
    "work_minutes": "50",
    "break_minutes": "10",
    "deadline_warning_days": "2",
    "sound_enabled": "1",
    "appearance_mode": "dark",
}

DEFAULT_CATEGORIES = ["ACRA Bitirme Projesi", "Olasılık", "Workout"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS Categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS Tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    parent_id     INTEGER REFERENCES Tasks(id) ON DELETE CASCADE,
    is_done       INTEGER NOT NULL DEFAULT 0,
    deadline      TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS TimeLogs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id       INTEGER NOT NULL REFERENCES Categories(id) ON DELETE CASCADE,
    log_date          TEXT    NOT NULL,
    duration_seconds  INTEGER NOT NULL,
    mode              TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS Settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_parent ON Tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_timelogs_date ON TimeLogs(log_date);
"""


@dataclass
class Category:
    id: int
    name: str


@dataclass
class Task:
    id: int
    title: str
    parent_id: int | None
    is_done: bool
    deadline: date | None
    completed_at: str | None
    subtasks: list["Task"] = field(default_factory=list)


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executescript(SCHEMA)
        self._seed_defaults()

    def close(self) -> None:
        self.conn.close()

    def _seed_defaults(self) -> None:
        with self.conn:
            for key, value in DEFAULT_SETTINGS.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO Settings(key, value) VALUES (?, ?)", (key, value)
                )
            # Varsayılan kategoriler yalnızca ilk çalıştırmada eklenir;
            # kullanıcı silerse geri gelmez.
            seeded = self.conn.execute(
                "SELECT value FROM Settings WHERE key = 'seeded'"
            ).fetchone()
            if seeded is None:
                for name in DEFAULT_CATEGORIES:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO Categories(name) VALUES (?)", (name,)
                    )
                self.conn.execute("INSERT INTO Settings(key, value) VALUES ('seeded', '1')")

    # ================================================================ Ayarlar
    def get_setting(self, key: str) -> str:
        row = self.conn.execute("SELECT value FROM Settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else DEFAULT_SETTINGS.get(key, "")

    def get_int_setting(self, key: str) -> int:
        try:
            return int(self.get_setting(key))
        except ValueError:
            return int(DEFAULT_SETTINGS[key])

    def set_settings(self, values: dict[str, str]) -> None:
        with self.conn:
            for key, value in values.items():
                self.conn.execute(
                    "INSERT INTO Settings(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )

    # ============================================================ Kategoriler
    def get_categories(self) -> list[Category]:
        rows = self.conn.execute("SELECT id, name FROM Categories").fetchall()
        cats = [Category(r["id"], r["name"]) for r in rows]
        return sorted(cats, key=lambda c: tr_sort_key(c.name))

    def add_category(self, name: str) -> Category:
        name = " ".join(name.split())
        if not name:
            raise ValueError("Kategori adı boş olamaz.")
        if any(tr_lower(c.name) == tr_lower(name) for c in self.get_categories()):
            raise ValueError(f"“{name}” adında bir kategori zaten var.")
        with self.conn:
            cur = self.conn.execute("INSERT INTO Categories(name) VALUES (?)", (name,))
        return Category(cur.lastrowid, name)

    def delete_category(self, category_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM Categories WHERE id = ?", (category_id,))

    # ================================================================ Görevler
    def add_task(self, title: str, parent_id: int | None = None,
                 deadline: date | None = None) -> int:
        title = title.strip()
        if not title:
            raise ValueError("Görev adı boş olamaz.")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO Tasks(title, parent_id, deadline) VALUES (?, ?, ?)",
                (title, parent_id, deadline.isoformat() if deadline else None),
            )
            # Tamamlanmış bir ana göreve yeni alt görev eklenirse ana görev tekrar açılır.
            if parent_id is not None:
                self.conn.execute(
                    "UPDATE Tasks SET is_done = 0, completed_at = NULL WHERE id = ?",
                    (parent_id,),
                )
        return cur.lastrowid

    def delete_task(self, task_id: int) -> None:
        with self.conn:  # alt görevler ON DELETE CASCADE ile silinir
            self.conn.execute("DELETE FROM Tasks WHERE id = ?", (task_id,))

    def set_deadline(self, task_id: int, deadline: date | None) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE Tasks SET deadline = ? WHERE id = ?",
                (deadline.isoformat() if deadline else None, task_id),
            )

    def set_task_done(self, task_id: int, done: bool) -> None:
        """Görevi tamamlandı/tamamlanmadı yapar.

        * Ana görev tamamlanınca tüm alt görevleri de tamamlanır.
        * Bir alt görev geri açılırsa ana görevi de geri açılır.
        """
        row = self.conn.execute("SELECT parent_id FROM Tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return
        stamp = datetime.now().isoformat() if done else None
        with self.conn:
            self.conn.execute(
                "UPDATE Tasks SET is_done = ?, completed_at = ? WHERE id = ?",
                (int(done), stamp, task_id),
            )
            if row["parent_id"] is None and done:
                self.conn.execute(
                    "UPDATE Tasks SET is_done = 1, completed_at = ? "
                    "WHERE parent_id = ? AND is_done = 0",
                    (stamp, task_id),
                )
            elif row["parent_id"] is not None and not done:
                self.conn.execute(
                    "UPDATE Tasks SET is_done = 0, completed_at = NULL WHERE id = ?",
                    (row["parent_id"],),
                )

    def get_task_tree(self) -> list[Task]:
        """Ana görevleri alt görevleriyle döndürür.

        Sıralama: tamamlanmamışlar eklenme sırasına göre üstte, tamamlananlar
        tamamlanma zamanına göre en altta (en son tamamlanan en altta).
        """
        rows = self.conn.execute("SELECT * FROM Tasks").fetchall()
        tasks: dict[int, Task] = {}
        for r in rows:
            tasks[r["id"]] = Task(
                id=r["id"],
                title=r["title"],
                parent_id=r["parent_id"],
                is_done=bool(r["is_done"]),
                deadline=date.fromisoformat(r["deadline"]) if r["deadline"] else None,
                completed_at=r["completed_at"],
            )
        roots: list[Task] = []
        for t in tasks.values():
            if t.parent_id is None:
                roots.append(t)
            elif t.parent_id in tasks:
                tasks[t.parent_id].subtasks.append(t)

        def order(t: Task):
            return (t.is_done, t.completed_at or "", t.id)

        roots.sort(key=order)
        for t in roots:
            t.subtasks.sort(key=order)
        return roots

    # ========================================================== Süre kayıtları
    def add_time_log(self, category_id: int, seconds: int,
                     log_date: date | None = None, mode: str = "") -> None:
        if seconds <= 0:
            return
        with self.conn:
            self.conn.execute(
                "INSERT INTO TimeLogs(category_id, log_date, duration_seconds, mode) "
                "VALUES (?, ?, ?, ?)",
                (category_id, (log_date or date.today()).isoformat(), int(seconds), mode),
            )

    def get_seconds_on(self, day: date, category_id: int | None = None) -> int:
        sql = "SELECT COALESCE(SUM(duration_seconds), 0) FROM TimeLogs WHERE log_date = ?"
        params: list = [day.isoformat()]
        if category_id is not None:
            sql += " AND category_id = ?"
            params.append(category_id)
        return int(self.conn.execute(sql, params).fetchone()[0])

    def get_category_totals(self, start: date, end: date) -> list[tuple[str, int]]:
        """[start, end] aralığında kategori başına toplam saniye (büyükten küçüğe)."""
        rows = self.conn.execute(
            "SELECT c.name AS name, SUM(t.duration_seconds) AS total "
            "FROM TimeLogs t JOIN Categories c ON c.id = t.category_id "
            "WHERE t.log_date BETWEEN ? AND ? "
            "GROUP BY c.id HAVING total > 0 ORDER BY total DESC",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [(r["name"], int(r["total"])) for r in rows]

    def get_daily_totals(self, start: date, end: date) -> list[tuple[date, int]]:
        """[start, end] aralığındaki her gün için toplam saniye (boş günler 0)."""
        rows = self.conn.execute(
            "SELECT log_date, SUM(duration_seconds) AS total FROM TimeLogs "
            "WHERE log_date BETWEEN ? AND ? GROUP BY log_date",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        by_day = {r["log_date"]: int(r["total"]) for r in rows}
        days = (end - start).days + 1
        return [
            (start + timedelta(days=i), by_day.get((start + timedelta(days=i)).isoformat(), 0))
            for i in range(days)
        ]
