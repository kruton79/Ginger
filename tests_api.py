import json
import os
import tempfile

import storage
storage.DB = os.path.join(tempfile.mkdtemp(), "test.db")  # ДО імпорту app!

import app as appmod

client = appmod.app.test_client()

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
    assert client.delete(f"/items/{new_id}").get_json() == {"deleted": new_id}
    assert_json_error(client.delete(f"/items/{new_id}"), 404)


def test_bad_body():
    assert_json_error(client.post("/items"), 400)
    assert_json_error(post_raw("{зламаний"), 400)
    assert_json_error(post_raw("[1, 2]"), 400)
    assert_json_error(post_raw("null"), 400)
    assert_json_error(post_raw(b'\xff\xfe{"a":1}'), 400)
    assert_json_error(post_raw(GOOD, "application/x-www-form-urlencoded"), 400)
    assert_json_error(post_raw("{}"), 400)
    # глибока вкладеність раніше давала 500 (RecursionError)
    assert_json_error(post_raw("[" * 9000), 400)
    assert_json_error(post_raw("[" * 4000 + "]" * 4000), 400)
    assert_json_error(post_raw("[" * 100000), 413)  # завеликий, відсікається ще до розбору


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


def test_text_fields():
    for bad in (None, "", "не дата", "2026-13-45", "2026-02-30", 123, ["2026-10-10"], "2026-10-10" + "0" * 50):
        assert_json_error(post(date=bad), 400)
    for bad in (None, "", "   ", {"a": 1}, 123, "x" * 101, "a\x00b"):
        assert_json_error(post(exercise=bad), 400)
    for bad in (["a"], 5, "n" * 501, "a\x00b"):
        assert_json_error(post(note=bad), 400)
    # одинокий сурогат раніше давав 500 (UnicodeEncodeError у SQLite)
    body = '{"date":"2026-10-10","exercise":"\\ud800","target_sets":1,"sets":1,"reps":1}'
    assert_json_error(post_raw(body), 400)


def test_text_is_normalized():
    r = post(date="2026-1-5", exercise="\t Відтискання  \n", note="  Все   добре ")
    assert r.status_code == 201
    item = [i for i in client.get("/items").get_json() if i["id"] == r.get_json()["id"]][0]
    assert item["date"] == "2026-01-05"          # дата в єдиному форматі
    assert item["exercise"] == "Відтискання"     # зайві пробіли, табуляції, переноси прибрано
    assert item["note"] == "Все добре"           # внутрішні пробіли теж зведено до одного
    r = post(note=None)
    item = [i for i in client.get("/items").get_json() if i["id"] == r.get_json()["id"]][0]
    assert item["note"] == ""                    # раніше зберігалося слово "None"


def test_body_size_limit():
    r = post(note="x" * (appmod.MAX_BODY_BYTES + 1))
    assert_json_error(r, 413)
    big = '{"date":"2026-10-10","exercise":"' + "a" * 5_000_000 + '","target_sets":1,"sets":1,"reps":1}'
    assert_json_error(post_raw(big), 413)


def test_filter():
    post()
    assert len(client.get("/items?exercise=Відтискання").get_json()) >= 1
    # регістр і зайві пробіли не мають значення
    assert len(client.get("/items?exercise=  відТИСКАННЯ ").get_json()) >= 1
    assert client.get("/items?exercise=Невідома вправа").get_json() == []
    assert client.get("/items?exercise=' OR 1=1 --").get_json() == []
    assert client.get("/items?exercise=%ff%00").status_code == 200
    assert_json_error(client.get("/items?exercise="), 400)


def test_delete_ids():
    for bad in ("abc", "-1", "1.5", "0", "%D1%84", "١٢٣"):
        assert_json_error(client.delete(f"/items/{bad}"), 400)
    for missing in ("99999", "9" * 30, "9223372036854775808", "9" * 5000):
        assert_json_error(client.delete(f"/items/{missing}"), 404)


def test_unknown_routes_and_methods_are_json():
    assert_json_error(client.get("/nope"), 404)
    assert_json_error(client.get("/"), 404)
    r = client.put("/items")
    assert_json_error(r, 405)
    assert "POST" in r.headers["Allow"]
    assert_json_error(client.post("/report"), 405)
    assert_json_error(client.get("/items/1"), 405)


def test_unexpected_error_is_hidden(monkeypatch=None):
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


def test_db_path_does_not_depend_on_cwd():
    # шлях до бази має бути абсолютним (не "data.db" відносно поточної папки)
    import importlib
    fresh = importlib.reload(storage)
    try:
        assert os.path.isabs(fresh.DB) and fresh.DB.endswith("data.db")
    finally:
        fresh.DB = os.path.join(tempfile.mkdtemp(), "test.db")
        fresh.init()


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
