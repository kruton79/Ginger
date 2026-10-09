def find_by_exercise(records, exercise):
    """Повертає записи для конкретної вправи."""
    if not exercise:
        return []
    return [r for r in records if r["exercise"].lower() == exercise.lower().strip()]


def total_stats_by_exercise(records):
    """Обчислює планові та фактичні підходи/повторення."""
    stats = {}
    for r in records:
        ex = r["exercise"]
        if ex not in stats:
            stats[ex] = {"target_sets": 0, "actual_sets": 0, "total_reps": 0}
        stats[ex]["target_sets"] += r["target_sets"]
        stats[ex]["actual_sets"] += r["sets"]
        stats[ex]["total_reps"] += r["reps"] * r["sets"]
    return stats