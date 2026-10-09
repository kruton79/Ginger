# cli.py
import sys
import storage
import logic

FILE = "data.txt"

def main():
    if len(sys.argv) < 2:
        print("Використання: python cli.py add|list|find|report ...")
        return

    command = sys.argv[1]
    records = storage.load(FILE)

    if command == "add":
        if len(sys.argv) < 6:
            print("Використання: python cli.py add ДАТА ВПРАВА ПОВТОРИ ПІДХОДИ [КОМЕНТАР]")
            return
        
        try:
            reps = int(sys.argv[4])
            sets = int(sys.argv[5])
        except ValueError:
            print("Помилка: повтори та підходи мають бути цілими числами!")
            return

        if reps <= 0 or sets <= 0:
            print("Помилка: кількість повторів і підходів має бути більшою за 0!")
            return

        note = sys.argv[6] if len(sys.argv) > 6 else ""
        records.append({
            "date": sys.argv[2],
            "exercise": sys.argv[3],
            "reps": reps,
            "sets": sets,
            "note": note
        })
        storage.save(FILE, records)
        print("Запис тренування успішно додано.")

    elif command == "list":
        if not records:
            print("Записів немає.")
            return
        for r in records:
            print(f"{r['date']} | {r['exercise']:<15} | {r['sets']} підх. x {r['reps']} повт. | {r['note']}")

    elif command == "find":
        if len(sys.argv) < 3:
            print("Використання: python cli.py find ВПРАВА")
            return
        found = logic.find_by_exercise(records, sys.argv[2])
        if not found:
            print("Записів не знайдено.")
            return
        for r in found:
            print(f"{r['date']} | {r['exercise']:<15} | {r['sets']} підх. x {r['reps']} повт. | {r['note']}")

    elif command == "report":
        stats = logic.total_stats_by_exercise(records)
        if not stats:
            print("Немає даних для звіту.")
            return
        for ex, data in stats.items():
            print(f"{ex:<15}: усього підходів = {data['total_sets']}, загалом повторень = {data['total_reps']}")

    else:
        print("Невідома команда:", command)

if __name__ == "__main__":
    main()