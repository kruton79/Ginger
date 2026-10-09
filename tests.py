import logic

def test_find_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Присідання", "reps": 15, "sets": 3, "note": "Ок"},
        {"date": "2026-10-02", "exercise": "Відтискання", "reps": 20, "sets": 4, "note": "Важко"}
    ]
    res = logic.find_by_exercise(records, "Присідання")
    assert len(res) == 1
    assert res[0]["reps"] == 15
    
    assert len(logic.find_by_exercise(records, "Тяга")) == 0
    assert len(logic.find_by_exercise([], "Присідання")) == 0
    assert len(logic.find_by_exercise(records, "")) == 0


def test_total_stats_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Присідання", "reps": 10, "sets": 3, "note": ""},
        {"date": "2026-10-02", "exercise": "Присідання", "reps": 12, "sets": 2, "note": ""}
    ]
    stats = logic.total_stats_by_exercise(records)
    assert stats["Присідання"]["total_sets"] == 5
    assert stats["Присідання"]["total_reps"] == 54
    assert logic.total_stats_by_exercise([]) == {}

if __name__ == "__main__":
    test_total_stats_by_exercise()
    test_find_by_exercise()
    print("Усі тести пройдено успішно!")