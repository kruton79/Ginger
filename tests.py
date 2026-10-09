import logic

def test_find_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Присідання", "target_sets": 4, "sets": 4, "reps": 15, "note": "Ок"},
        {"date": "2026-10-02", "exercise": "Відтискання", "target_sets": 4, "sets": 2, "reps": 20, "note": "Важко"}
    ]
    res = logic.find_by_exercise(records, "Присідання")
    assert len(res) == 1
    assert res[0]["reps"] == 15
    
    assert len(logic.find_by_exercise(records, "Тяга")) == 0
    assert len(logic.find_by_exercise([], "Присідання")) == 0
    assert len(logic.find_by_exercise(records, "")) == 0


def test_total_stats_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Присідання", "target_sets": 4, "sets": 3, "reps": 10, "note": ""},
        {"date": "2026-10-02", "exercise": "Присідання", "target_sets": 4, "sets": 2, "reps": 12, "note": ""}
    ]
    stats = logic.total_stats_by_exercise(records)
    assert stats["Присідання"]["actual_sets"] == 5
    assert stats["Присідання"]["target_sets"] == 8
    assert stats["Присідання"]["total_reps"] == 54
    assert logic.total_stats_by_exercise([]) == {}

if __name__ == "__main__":
    test_total_stats_by_exercise()
    test_find_by_exercise()
    print("Усі тести пройдено успішно!")