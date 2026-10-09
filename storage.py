def load(filename):
    """Повертає список словників з файла. Пошкоджені рядки пропускає."""
    records = []
    try:
        f = open(filename, "r", encoding="utf-8")
    except FileNotFoundError:
        return records

    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            try:
                record = {
                    "date": parts[0],
                    "exercise": parts[1],
                    "reps": int(parts[2]),
                    "sets": int(parts[3]),
                    "note": parts[4] if len(parts) > 4 else ""
                }
                records.append(record)
            except (IndexError, ValueError):
                print("Пропущено пошкоджений рядок:", line)
                continue
    return records


def save(filename, records):
    """Записує всі записи у файл. Очищає спецсимволи ';'."""
    with open(filename, "w", encoding="utf-8") as f:
        for r in records:
            clean_ex = str(r['exercise']).replace(";", ",")
            clean_note = str(r['note']).replace(";", ",")
            f.write(f"{r['date']};{clean_ex};{r['reps']};{r['sets']};{clean_note}\n")