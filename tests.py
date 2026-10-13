import logic

def test_find_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Відтискання", "target_sets": 4, "sets": 4, "reps": 15, "note": "Ок"},
        {"date": "2026-10-02", "exercise": "Відтискання", "target_sets": 4, "sets": 2, "reps": 20, "note": "Важко"}
    ]
    res = logic.find_by_exercise(records, "Відтискання")
    assert len(res) == 2
    assert res[0]["reps"] == 15
    assert res[1]["reps"] == 20

    assert len(logic.find_by_exercise(records, "відтискання")) == 2      # регістр не важливий
    assert len(logic.find_by_exercise(records, "  Відтискання ")) == 2   # зайві пробіли не заважають
    assert len(logic.find_by_exercise(records, "Невідома вправа")) == 0
    assert len(logic.find_by_exercise([], "Відтискання")) == 0
    assert len(logic.find_by_exercise(records, "")) == 0


def test_total_stats_by_exercise():
    records = [
        {"date": "2026-10-01", "exercise": "Відтискання", "target_sets": 4, "sets": 3, "reps": 10, "note": ""},
        {"date": "2026-10-02", "exercise": "Відтискання", "target_sets": 4, "sets": 2, "reps": 12, "note": ""}
    ]
    stats = logic.total_stats_by_exercise(records)
    assert stats["Відтискання"]["actual_sets"] == 5
    assert stats["Відтискання"]["target_sets"] == 8
    assert stats["Відтискання"]["total_reps"] == 54
    assert len(stats) == 1  # усі записи про одну вправу
    assert logic.total_stats_by_exercise([]) == {}

if __name__ == "__main__":
    test_total_stats_by_exercise()
    test_find_by_exercise()
    print("Усі тести пройдено успішно!")