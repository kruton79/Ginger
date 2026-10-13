import sqlite3

DB = "data.db"

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row  # Щоб рядки читалися як словники
    return conn

def init():
    """Створює таблицю, якщо її ще немає."""
    with connect() as conn:
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
    with connect() as conn:
        if exercise is None:
            rows = conn.execute("SELECT * FROM items ORDER BY date").fetchall()
        else:
            # Використовуємо ? для захисту від SQL-ін'єкцій!
            rows = conn.execute("SELECT * FROM items WHERE exercise = ? ORDER BY date", (exercise,)).fetchall()
    
    result = []
    for row in rows:
        result.append(dict(row))
    return result

def add(date, exercise, target_sets, sets, reps, note=""):
    """Додає запис і повертає його id."""
    with connect() as conn:
        cur = conn.execute("INSERT INTO items (date, exercise, target_sets, sets, reps, note) VALUES (?, ?, ?, ?, ?, ?)",
                           (date, exercise, target_sets, sets, reps, note))
        return cur.lastrowid

def delete(item_id):
    """Видаляє запис. Повертає True, якщо він існував."""
    with connect() as conn:
        cur = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        return cur.rowcount > 0