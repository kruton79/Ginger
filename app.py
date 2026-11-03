import hmac
import os
import re
import sqlite3
import unicodedata
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import storage
import logic

# Секрети беремо з файлу .env поруч з app.py (його немає в git) або зі змінних оточення.
# Змінні, які вже задані в оточенні, load_dotenv не перезаписує.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

# --- Обмеження на вхідні дані ---
# Без них один запит на 100 МБ потрапляє в базу, і після цього кожен GET /items
# віддає 100 МБ, тобто сервіс фактично лежить.
MAX_BODY_BYTES = 10 * 1024   # весь запит не більше 10 КБ
MAX_NUMBER = 10_000          # максимум для target_sets, sets, reps
MAX_EXERCISE_LEN = 100
MAX_NOTE_LEN = 500
MAX_ID = 2**63 - 1           # більше SQLite INTEGER не тримає
MAX_IMPORT_BYTES = 1_000_000  # імпорт з адмінки може бути більшим за звичайний запит
MAX_IMPORT_ITEMS = 1000       # і не більше стількох записів за раз

app = Flask(__name__)

# Вимикаємо кодування кирилиці в \uXXXX, щоб помилки читалися нормально
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

# Браузер пускає на API лише наш фронтенд (CORS). origins="*" не використовуємо.
CORS(app, origins=["https://shylko.pp.ua"])

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


def parse_item(data):
    """Перевіряє один запис. Повертає (date, exercise, target_sets, sets, reps, note)
    або кидає ValueError з поясненням. Спільна для POST /items та POST /admin/import."""
    if not isinstance(data, dict):
        raise ValueError("Запис має бути JSON-об'єктом")
    missing = [f for f in ["date", "exercise", "target_sets", "sets", "reps"] if f not in data]
    if missing:
        raise ValueError(f"Відсутні обов'язкові поля: {', '.join(missing)}")
    return (
        parse_date(data["date"]),
        clean_text(data["exercise"], "exercise", MAX_EXERCISE_LEN),
        parse_int(data["target_sets"], "target_sets"),
        parse_int(data["sets"], "sets"),
        parse_int(data["reps"], "reps"),
        clean_text(data.get("note"), "note", MAX_NOTE_LEN, required=False),
    )


def read_json():
    """Тіло запиту як JSON або None, якщо воно зламане чи надто вкладене."""
    try:
        return request.get_json(silent=True)
    except RecursionError:  # JSON з надмірною вкладеністю [[[[...
        return None


def require_admin():
    """Адмінка лише з цього комп'ютера (не через Cloudflare) і лише з токеном."""
    # Cloudflare додає CF-Connecting-IP до кожного запиту, що пройшов через нього, і прибрати
    # цей заголовок ззовні неможливо. Є заголовок, отже запит з інтернету: адмінки для нього немає.
    if "CF-Connecting-IP" in request.headers:
        app.logger.warning("Запит до /admin/ через Cloudflare відхилено: %r", request.path)
        abort(404)
    token = request.headers.get("X-Admin-Token", "")
    # Порожній ADMIN_TOKEN (секрет не налаштовано) не має пускати нікого,
    # навіть запит без заголовка. Порівняння у постійний час.
    if not ADMIN_TOKEN or not hmac.compare_digest(token.encode(), ADMIN_TOKEN.encode()):
        abort(403)


# --- Єдиний формат помилок: завжди JSON, ніколи HTML і ніколи traceback ---

@app.errorhandler(HTTPException)
def handle_http_error(e):
    messages = {
        403: "Доступ заборонено",
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
    data = read_json()
    if not isinstance(data, dict):
        return error("Отримано невалідний JSON або дані відсутні", 400)
    try:
        values = parse_item(data)
    except ValueError as e:
        return error(str(e), 400)
    new_id = storage.add(*values)
    return jsonify({"id": new_id, "message": "Запис успішно додано"}), 201


@app.get("/report")
def report():
    return jsonify(logic.total_stats_by_exercise(storage.load()))


# --- Адмінка: з інтернету недоступна (правило в deploy/cloudflared.yml), лише з токеном ---

@app.delete("/admin/items/<item_id>")
def admin_delete_item(item_id):
    require_admin()
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


@app.get("/admin/export")
def admin_export():
    require_admin()
    return jsonify(storage.load())


@app.post("/admin/import")
def admin_import():
    require_admin()
    try:
        request.max_content_length = MAX_IMPORT_BYTES  # Flask 3.1+: ліміт лише для цього запиту
    except AttributeError:
        pass  # старіший Flask: лишається загальний ліміт
    data = read_json()
    if not isinstance(data, list) or not data:
        return error("Очікується непорожній JSON-список записів", 400)
    if len(data) > MAX_IMPORT_ITEMS:
        return error(f"Забагато записів за раз (максимум {MAX_IMPORT_ITEMS})", 400)
    rows = []
    for number, item in enumerate(data, start=1):
        try:
            rows.append(parse_item(item))
        except ValueError as e:
            return error(f"Запис {number}: {e}", 400)
    count = storage.add_many(rows)  # одна транзакція: або всі записи, або жоден
    return jsonify({"imported": count}), 201


if __name__ == "__main__":
    # debug НЕ вмикаємо за замовчуванням: інтерактивний налагоджувач Werkzeug
    # дозволяє виконувати код на сервері. Для розробки: FLASK_DEBUG=1 python app.py
    app.run()
