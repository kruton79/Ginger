def find_by_exercise(records, exercise):
    """Повертає записи для конкретної вправи."""
    if not exercise:
        return []
    return [r for r in records if r["exercise"].lower() == exercise.lower().strip()]


def total_stats_by_exercise(records):
    """
    Повертає підсумки по кожній вправі у вигляді:
    { "Назва вправи": {"total_sets": X, "total_reps": Y} }
    """
    stats = {}
    for r in records:
        ex = r["exercise"]
        if ex not in stats:
            stats[ex] = {"total_sets": 0, "total_reps": 0}
        stats[ex]["total_sets"] += r["sets"]
        stats[ex]["total_reps"] += r["reps"] * r["sets"]
    return stats