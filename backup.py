"""Копіює базу в теку backups поруч зі скриптом, з датою в назві."""
import datetime
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data.db")
BACKUPS = os.path.join(BASE, "backups")

os.makedirs(BACKUPS, exist_ok=True)
target = os.path.join(BACKUPS, f"data-{datetime.date.today()}.db")
src = sqlite3.connect(DB)
dst = sqlite3.connect(target)
src.backup(dst)                        # коректна копія навіть під час роботи сервісу
dst.close()
src.close()
print("збережено", target)
