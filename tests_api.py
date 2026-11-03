"""Перевірки HTTP-маршрутів. Запуск: python tests_api.py (або pytest tests_api.py).
Використовує окрему тимчасову базу, ваш data.db не чіпає."""
import os
import tempfile

import storage
storage.DB = os.path.join(tempfile.mkdtemp(), "test.db")  # ДО імпорту app!
os.environ["ADMIN_TOKEN"] = "test-token"  # теж ДО імпорту app: так тести не залежать від вашого .env

import app as appmod

client = appmod.app.test_client()

ADMIN = {"X-Admin-Token": "test-token"}
GOOD = {"date": "2026-10-10", "exercise": "Відтискання", "target_sets": 4, "sets": 4, "reps": 20, "note": "ок"}


def post(**changes):
    body = dict(GOOD)
    body.update(changes)
    return client.post("/items", json=body)


def post_raw(data, content_type="application/json"):
    return client.post("/items", data=data, content_type=content_type)


def assert_json_error(resp, code):
    """Помилка має бути JSON з полем error і правильним кодом, а не HTML і не 500."""
    assert resp.status_code == code, f"очікувався {code}, отримано {resp.status_code}: {resp.get_data(as_text=True)[:100]}"
    assert resp.is_json, "відповідь на помилку не JSON"
    assert "error" in resp.get_json()


def test_happy_path():
    r = post()
    assert r.status_code == 201
    new_id = r.get_json()["id"]
    assert any(i["id"] == new_id for i in client.get("/items").get_json())
    assert client.get("/report").get_json()["Відтискання"]["actual_sets"] >= 4
    assert client.delete(f"/admin/items/{new_id}", headers=ADMIN).get_json() == {"deleted": new_id}
    assert_json_error(client.delete(f"/admin/items/{new_id}", headers=ADMIN), 404)


def test_db_path_does_not_depend_on_cwd():
    # шлях до бази має бути абсолютним (не "data.db" відносно поточної папки)
    import importlib
    fresh = importlib.reload(storage)
    try:
        assert os.path.isabs(fresh.DB) and fresh.DB.endswith("data.db")
    finally:
        fresh.DB = os.path.join(tempfile.mkdtemp(), "test.db")
        fresh.init()


def test_connection_is_closed_after_use():
    import sqlite3
    with storage.db() as conn:
        conn.execute("SELECT 1")
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return
    raise AssertionError("з'єднання лишилося відкритим")


def test_unknown_routes_and_methods_are_json():
    assert_json_error(client.get("/nope"), 404)
    assert_json_error(client.get("/"), 404)
    assert_json_error(client.put("/items"), 405)
    assert_json_error(client.post("/report"), 405)
    assert_json_error(client.get("/items/1"), 404)  # публічного маршруту /items/<id> більше немає


def test_405_has_allow_header():
    r = client.put("/items")
    assert "POST" in r.headers["Allow"]


def test_database_error_is_503():
    import sqlite3
    original = storage.load
    def locked(*a, **k):
        raise sqlite3.OperationalError("database is locked")
    storage.load = locked
    try:
        r = client.get("/report")
    finally:
        storage.load = original
    assert_json_error(r, 503)


def test_unexpected_error_is_hidden():
    """Непередбачена помилка: JSON 500 без traceback і без внутрішніх деталей."""
    original = storage.load
    def boom(*a, **k):
        raise RuntimeError("секретна внутрішня деталь")
    storage.load = boom
    try:
        r = client.get("/items")
    finally:
        storage.load = original
    assert_json_error(r, 500)
    assert "секретна" not in r.get_data(as_text=True)


def test_body_size_limit():
    r = post(note="x" * (appmod.MAX_BODY_BYTES + 1))
    assert_json_error(r, 413)
    big = '{"date":"2026-10-10","exercise":"' + "a" * 5_000_000 + '","target_sets":1,"sets":1,"reps":1}'
    assert_json_error(post_raw(big), 413)
    assert_json_error(post_raw("[" * 100000), 413)


def test_bad_body():
    assert_json_error(client.post("/items"), 400)
    assert_json_error(post_raw("{зламаний"), 400)
    assert_json_error(post_raw("[1, 2]"), 400)
    assert_json_error(post_raw("null"), 400)
    assert_json_error(post_raw(b'\xff\xfe{"a":1}'), 400)
    assert_json_error(post_raw(GOOD, "application/x-www-form-urlencoded"), 400)
    assert_json_error(post_raw("{}"), 400)
    assert_json_error(post_raw("[" * 9000), 400)
    assert_json_error(post_raw("[" * 4000 + "]" * 4000), 400)


def test_json_recursion_error_is_400():
    # на деяких версіях Python надто вкладений JSON кидає RecursionError, імітуємо це
    from flask import Request
    original = Request.get_json
    def boom(self, *a, **k):
        raise RecursionError
    Request.get_json = boom
    try:
        r = post_raw("{}")
    finally:
        Request.get_json = original
    assert_json_error(r, 400)


def test_numbers():
    for field in ("target_sets", "sets", "reps"):
        for bad in (None, "abc", 2.7, True, [1], {"a": 1}, -1, 10**30, 2**63,
                    "inf", "1e400", "9" * 5000, 10_001, ""):
            assert_json_error(post(**{field: bad}), 400)
        assert post(**{field: "3"}).status_code == 201   # "3" як рядок допустимо
        assert post(**{field: 0}).status_code == 201
    # Infinity / 1e999 у "сирому" JSON раніше давали 500 (OverflowError)
    for raw_value in ("Infinity", "-Infinity", "NaN", "1e999"):
        body = '{"date":"2026-10-10","exercise":"x","target_sets":%s,"sets":1,"reps":1}' % raw_value
        assert_json_error(post_raw(body), 400)


def test_exercise_and_note_validation():
    for bad in (None, "", "   ", {"a": 1}, 123, "x" * 101, "a\x00b"):
        assert_json_error(post(exercise=bad), 400)
    for bad in (["a"], 5, "n" * 501, "a\x00b"):
        assert_json_error(post(note=bad), 400)
    # одинокий сурогат раніше давав 500 (UnicodeEncodeError у SQLite)
    body = '{"date":"2026-10-10","exercise":"\\ud800","target_sets":1,"sets":1,"reps":1}'
    assert_json_error(post_raw(body), 400)


def test_exercise_and_note_are_normalized():
    r = post(exercise="\t Відтискання  \n", note="  Все   добре ")
    assert r.status_code == 201
    item = [i for i in client.get("/items").get_json() if i["id"] == r.get_json()["id"]][0]
    assert item["exercise"] == "Відтискання"     # зайві пробіли, табуляції, переноси прибрано
    assert item["note"] == "Все добре"           # внутрішні пробіли теж зведено до одного
    r = post(note=None)
    item = [i for i in client.get("/items").get_json() if i["id"] == r.get_json()["id"]][0]
    assert item["note"] == ""                    # раніше зберігалося слово "None"


def test_date_validation():
    for bad in (None, "", "не дата", "2026-13-45", "2026-02-30", 123, ["2026-10-10"], "2026-10-10" + "0" * 50):
        assert_json_error(post(date=bad), 400)
    r = post(date="2026-1-5")
    assert r.status_code == 201
    item = [i for i in client.get("/items").get_json() if i["id"] == r.get_json()["id"]][0]
    assert item["date"] == "2026-01-05"          # дата в єдиному форматі


def test_delete_ids():
    for bad in ("abc", "-1", "1.5", "0", "%D1%84", "١٢٣"):
        assert_json_error(client.delete(f"/admin/items/{bad}", headers=ADMIN), 400)
    for missing in ("99999", "9" * 30, "9223372036854775808", "9" * 5000):
        assert_json_error(client.delete(f"/admin/items/{missing}", headers=ADMIN), 404)


def test_filter():
    post()
    assert len(client.get("/items?exercise=Відтискання").get_json()) >= 1
    # регістр і зайві пробіли не мають значення
    assert len(client.get("/items?exercise=  відТИСКАННЯ ").get_json()) >= 1
    assert client.get("/items?exercise=Невідома вправа").get_json() == []
    assert client.get("/items?exercise=' OR 1=1 --").get_json() == []
    assert client.get("/items?exercise=%ff%00").status_code == 200
    assert_json_error(client.get("/items?exercise="), 400)


def test_cors_allows_only_our_frontend():
    good = client.options("/items", headers={"Origin": "https://shylko.pp.ua", "Access-Control-Request-Method": "POST"})
    assert good.headers.get("Access-Control-Allow-Origin") == "https://shylko.pp.ua"
    bad = client.options("/items", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in bad.headers
    plain = client.get("/items", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in plain.headers


def test_old_public_delete_is_gone():
    # видалення тепер лише в адмінці, а публічний DELETE /items/<id> не існує
    assert_json_error(client.delete("/items/1"), 404)


def test_admin_requires_token():
    assert_json_error(client.get("/admin/export"), 403)                                    # без токена
    assert_json_error(client.get("/admin/export", headers={"X-Admin-Token": "wrong"}), 403)  # хибний токен
    assert client.get("/admin/export", headers=ADMIN).status_code == 200
    assert_json_error(client.delete("/admin/items/1"), 403)
    assert_json_error(client.post("/admin/import", json=[GOOD]), 403)


def test_admin_hidden_from_internet():
    # Cloudflare додає CF-Connecting-IP: запит з інтернету бачить 404 навіть з правильним токеном
    internet = {"X-Admin-Token": "test-token", "CF-Connecting-IP": "203.0.113.7"}
    assert_json_error(client.get("/admin/export", headers=internet), 404)
    assert_json_error(client.delete("/admin/items/1", headers=internet), 404)
    assert_json_error(client.post("/admin/import", json=[GOOD], headers=internet), 404)


def test_admin_closed_when_token_not_configured():
    # якщо ADMIN_TOKEN не задано, запит без заголовка не має проходити (None == None пропустило б його)
    original = appmod.ADMIN_TOKEN
    appmod.ADMIN_TOKEN = ""
    try:
        assert_json_error(client.get("/admin/export"), 403)
        assert_json_error(client.get("/admin/export", headers={"X-Admin-Token": ""}), 403)
    finally:
        appmod.ADMIN_TOKEN = original


def test_admin_export_import_roundtrip():
    before = len(client.get("/admin/export", headers=ADMIN).get_json())
    items = [dict(GOOD, exercise="Імпорт 1"), dict(GOOD, exercise="Імпорт 2", date="2026-1-5")]
    r = client.post("/admin/import", json=items, headers=ADMIN)
    assert r.status_code == 201 and r.get_json() == {"imported": 2}
    exported = client.get("/admin/export", headers=ADMIN).get_json()
    assert len(exported) == before + 2
    assert any(i["exercise"] == "Імпорт 2" and i["date"] == "2026-01-05" for i in exported)


def test_admin_import_is_all_or_nothing():
    before = len(client.get("/admin/export", headers=ADMIN).get_json())
    r = client.post("/admin/import", json=[dict(GOOD), dict(GOOD, sets="abc")], headers=ADMIN)
    assert_json_error(r, 400)
    assert "Запис 2" in r.get_json()["error"]
    assert len(client.get("/admin/export", headers=ADMIN).get_json()) == before   # не додано навіть перший


def test_admin_import_limits():
    for bad in ({"a": 1}, [], "текст", [1, 2], [[]]):
        assert_json_error(client.post("/admin/import", json=bad, headers=ADMIN), 400)
    assert_json_error(client.post("/admin/import", json=[GOOD] * (appmod.MAX_IMPORT_ITEMS + 1), headers=ADMIN), 400)
    # понад 10 КБ, але менше за ліміт імпорту: проходить (потрібен Flask 3.1+)
    r = client.post("/admin/import", json=[dict(GOOD, note="x" * 400)] * 60, headers=ADMIN)
    assert r.status_code == 201, "імпорт понад 10 КБ не пройшов: перевірте версію Flask (потрібна 3.1+)"
    big = '[{"note": "' + "a" * (appmod.MAX_IMPORT_BYTES + 10) + '"}]'
    assert_json_error(post_raw_admin(big), 413)


def post_raw_admin(data):
    return client.post("/admin/import", data=data, content_type="application/json", headers=ADMIN)


def test_sql_injection_is_just_text():
    evil = "'; DROP TABLE items; --"
    r = post(exercise=evil)
    assert r.status_code == 201
    items = client.get("/items").get_json()           # таблиця на місці
    assert any(i["exercise"] == evil for i in items)  # і рядок збережено як звичайний текст
    assert client.get("/items", query_string={"exercise": evil}).status_code == 200


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, func in tests:
        try:
            func()
            print("OK  ", name)
        except AssertionError as e:
            failed += 1
            print("FAIL", name, "-", e)
    print(f"\n{len(tests) - failed}/{len(tests)} тестів пройдено")
    raise SystemExit(1 if failed else 0)
