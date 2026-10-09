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
        if len(sys.argv) < 7:
            print("Використання: python cli.py add ДАТА ВПРАВА ПЛАН_ПІДХОДІВ ФАКТ_ПІДХОДІВ ПОВТОРИ [КОМЕНТАР]")
            return
        
        try:
            target_sets = int(sys.argv[4])
            sets = int(sys.argv[5])
            reps = int(sys.argv[6])
        except ValueError:
            print("Помилка: підходи та повтори мають бути цілими числами!")
            return

        if target_sets <= 0 or sets < 0 or reps <= 0:
            print("Помилка: підходи і повтори повинні бути більшими за 0!")
            return

        note = sys.argv[7] if len(sys.argv) > 7 else ""
        
        records.append({
            "date": sys.argv[2],
            "exercise": sys.argv[3],
            "target_sets": target_sets,
            "sets": sets,
            "reps": reps,
            "note": note
        })
        storage.save(FILE, records)
        print("Запис успішно додано.")

    elif command == "list":
        if not records:
            print("Записів немає.")
            return
        for r in records:
            status = " [НЕ ПОВНІСТЮ]" if r['sets'] < r['target_sets'] else " [ВИКОНАНО]"
            print(f"{r['date']} | {r['exercise']:<15} | {r['sets']}/{r['target_sets']} підх. x {r['reps']} повт.{status} | {r['note']}")

    elif command == "find":
        if len(sys.argv) < 3:
            print("Використання: python cli.py find ВПРАВА")
            return
        found = logic.find_by_exercise(records, sys.argv[2])
        if not found:
            print("Записів не знайдено.")
            return
        for r in found:
            status = " [НЕ ПОВНІСТЮ]" if r['sets'] < r['target_sets'] else " [ВИКОНАНО]"
            print(f"{r['date']} | {r['exercise']:<15} | {r['sets']}/{r['target_sets']} підх. x {r['reps']} повт.{status} | {r['note']}")

    elif command == "report":
        stats = logic.total_stats_by_exercise(records)
        if not stats:
            print("Немає даних для звіту.")
            return
        for ex, data in stats.items():
            print(f"{ex:<15}: виконано підходів = {data['actual_sets']}/{data['target_sets']}, загалом повторень = {data['total_reps']}")

    else:
        print("Невідома команда:", command)

if __name__ == "__main__":
    main()