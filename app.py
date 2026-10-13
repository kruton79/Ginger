import re
import sqlite3
import unicodedata
from datetime import datetime

from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

import storage
import logic

# --- Обмеження на вхідні дані ---
# Без них один запит на 100 МБ потрапляє в базу, і після цього кожен GET /items
# віддає 100 МБ, тобто сервіс фактично лежить.
MAX_BODY_BYTES = 10 * 1024   # весь запит не більше 10 КБ
MAX_NUMBER = 10_000          # максимум для target_sets, sets, reps
MAX_EXERCISE_LEN = 100
MAX_NOTE_LEN = 500
MAX_ID = 2**63 - 1           # більше SQLite INTEGER не тримає

app = Flask(__name__)

# Вимикаємо кодування кирилиці в \uXXXX, щоб помилки читалися нормально
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

storage.init()


def error(message, code):
    return jsonify({"error": message}), code


def parse_int(value, name):
    """Повертає ціле число 0..MAX_NUMBER або кидає ValueError з поясненням."""
    # bool це підклас int (True == 1), float мовчки обрізався б (2.7 -> 2): не пропускаємо
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"Поле {name} має бути цілим числом")
    if isinstance(value, str):
        value = value.strip()
        if len(value) > 20 or not re.fullmatch(r"-?\d+", value, re.ASCII):
            raise ValueError(f"Поле {name} має бути цілим числом")
    number = int(value)
    if not 0 <= number <= MAX_NUMBER:
        raise ValueError(f"Поле {name} має бути від 0 до {MAX_NUMBER}")
    return number


def clean_text(value, name, max_len, required=True):
    """Повертає охайний рядок або кидає ValueError з поясненням."""
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"Поле {name} має бути рядком")
    text = " ".join(value.split())  # прибирає зайві пробіли, табуляції, переноси
    # Cc: керівні символи (напр. \x00), Cs: "одинокі сурогати" (\ud800),
    # на яких SQLite/кодування UTF-8 падає з 500
    if any(unicodedata.category(ch) in ("Cc", "Cs") for ch in text):
        raise ValueError(f"Поле {name} містить недопустимі символи")
    if required and not text:
        raise ValueError(f"Поле {name} не може бути порожнім")
    if len(text) > max_len:
        raise ValueError(f"Поле {name} задовге (максимум {max_len} символів)")
    return text


def parse_date(value):
    """Перевіряє, що це справжня дата РРРР-ММ-ДД, і повертає її в єдиному форматі."""
    text = clean_text(value, "date", 10)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError("Поле date має бути існуючою датою у форматі РРРР-ММ-ДД")


# --- Єдиний формат помилок: завжди JSON, ніколи HTML і ніколи traceback ---

@app.errorhandler(HTTPException)
def handle_http_error(e):
    messages = {
        404: "Ресурс не знайдено",
        405: "Цей метод не підтримується для цього маршруту",
        413: f"Запит завеликий (максимум {MAX_BODY_BYTES} байт)",
    }
    response, code = error(messages.get(e.code, e.description), e.code)
    if e.code == 405 and getattr(e, "valid_methods", None):
        response.headers["Allow"] = ", ".join(e.valid_methods)
    return response, code


@app.errorhandler(sqlite3.Error)
def handle_db_error(e):
    app.logger.exception("Помилка бази даних")
    return error("База даних тимчасово недоступна, спробуйте пізніше", 503)


@app.errorhandler(Exception)
def handle_unexpected(e):
    app.logger.exception("Необроблена помилка")  # деталі лише в лог, не клієнтові
    return error("Внутрішня помилка сервера", 500)


# --- Маршрути ---

@app.get("/items")
def list_items():
    exercise = request.args.get("exercise")
    if exercise is None:
        return jsonify(storage.load())
    exercise = " ".join(exercise.split())
    if not exercise:
        return error("Параметр exercise не може бути порожнім", 400)
    # Фільтр у Python, а не в SQL: SQLite порівнює кирилицю з урахуванням регістру,
    # а logic.find_by_exercise знаходить "відтискання" і "Відтискання" як одну вправу
    return jsonify(logic.find_by_exercise(storage.load(), exercise))


@app.post("/items")
def add_item():
    try:
        data = request.get_json(silent=True)
    except RecursionError:  # JSON з надмірною вкладеністю [[[[...
        data = None

    # 1. Перевірка цілісності JSON (якщо PowerShell знову поламає лапки)
    if not isinstance(data, dict):
        return error("Отримано невалідний JSON або дані відсутні", 400)

    # 2. Перевірка наявності всіх обов'язкових ключів
    required_fields = ["date", "exercise", "target_sets", "sets", "reps"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return error(f"Відсутні обов'язкові поля: {', '.join(missing)}", 400)

    # 3. Перевірка типів, діапазонів і довжин усіх полів
    try:
        date = parse_date(data["date"])
        exercise = clean_text(data["exercise"], "exercise", MAX_EXERCISE_LEN)
        target_sets = parse_int(data["target_sets"], "target_sets")
        sets = parse_int(data["sets"], "sets")
        reps = parse_int(data["reps"], "reps")
        note = clean_text(data.get("note"), "note", MAX_NOTE_LEN, required=False)
    except ValueError as e:
        return error(str(e), 400)

    new_id = storage.add(date, exercise, target_sets, sets, reps, note)
    return jsonify({"id": new_id, "message": "Запис успішно додано"}), 201


@app.delete("/items/<item_id>")
def delete_item(item_id):
    # Не <int:item_id>: тоді "abc" і "-1" давали б HTML-сторінку 404 замість JSON
    if not (item_id.isascii() and item_id.isdigit()):
        return error("ID має бути додатним цілим числом", 400)
    if len(item_id) > 19 or int(item_id) > MAX_ID:  # такого id не може існувати
        return error("Запис з таким ID не знайдено", 404)
    number = int(item_id)
    if number < 1:
        return error("ID має бути додатним цілим числом", 400)
    if storage.delete(number):
        return jsonify({"deleted": number})
    return error(f"Запис з ID {number} не знайдено", 404)


@app.get("/report")
def report():
    return jsonify(logic.total_stats_by_exercise(storage.load()))


if __name__ == "__main__":
    # debug НЕ вмикаємо за замовчуванням: інтерактивний налагоджувач Werkzeug
    # дозволяє виконувати код на сервері. Для розробки: FLASK_DEBUG=1 python app.py
    app.run()
