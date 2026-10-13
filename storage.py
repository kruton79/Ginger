import os
import sqlite3
from contextlib import contextmanager

# Шлях рахуємо від розташування цього файлу, а не від поточної папки.
# Інакше запуск з іншого каталогу створив би нову порожню базу, і дані "зникли б".
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

def connect():
    conn = sqlite3.connect(DB, timeout=10)  # до 10 с чекаємо, якщо база зайнята
    conn.row_factory = sqlite3.Row  # Щоб рядки читалися як словники
    return conn

@contextmanager
def db():
    """Відкриває з'єднання, робить commit/rollback і ЗАВЖДИ закриває його.
    (Звичайний `with connect()` закриває лише транзакцію, а не з'єднання.)"""
    conn = connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init():
    """Створює таблицю, якщо її ще немає."""
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise TEXT NOT NULL,
            target_sets INTEGER NOT NULL,
            sets INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            note TEXT)""")

def load(exercise=None):
    """Повертає список записів. Якщо вказано exercise — фільтрує."""
    with db() as conn:
        if exercise is None:
            rows = conn.execute("SELECT * FROM items ORDER BY date, id").fetchall()
        else:
            # Використовуємо ? для захисту від SQL-ін'єкцій!
            rows = conn.execute("SELECT * FROM items WHERE exercise = ? ORDER BY date, id", (exercise,)).fetchall()

    result = []
    for row in rows:
        result.append(dict(row))
    return result

def add(date, exercise, target_sets, sets, reps, note=""):
    """Додає запис і повертає його id."""
    with db() as conn:
        cur = conn.execute("INSERT INTO items (date, exercise, target_sets, sets, reps, note) VALUES (?, ?, ?, ?, ?, ?)",
                           (date, exercise, target_sets, sets, reps, note))
        return cur.lastrowid

def delete(item_id):
    """Видаляє запис. Повертає True, якщо він існував."""
    with db() as conn:
        cur = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        return cur.rowcount > 0
