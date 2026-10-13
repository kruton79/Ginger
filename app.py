from flask import Flask, request, jsonify
import storage
import logic

app = Flask(__name__)

# Вимикаємо кодування кирилиці в \uXXXX, щоб помилки читалися нормально
app.json.ensure_ascii = False 

storage.init()

@app.get("/items")
def list_items():
    exercise = request.args.get("exercise")
    return jsonify(storage.load(exercise))

@app.post("/items")
def add_item():
    data = request.get_json(silent=True)
    
    # 1. Перевірка цілісності JSON (якщо PowerShell знову поламає лапки)
    if not isinstance(data, dict):
        return jsonify({"error": "Отримано невалідний JSON або дані відсутні"}), 400

    # 2. Перевірка наявності всіх обов'язкових ключів
    required_fields = ["date", "exercise", "target_sets", "sets", "reps"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Відсутні обов'язкові поля: {', '.join(missing)}"}), 400

    # 3. Універсальна перевірка числових полів
    try:
        target_sets = int(data["target_sets"])
        sets = int(data["sets"])
        reps = int(data["reps"])
        
        if target_sets < 0 or sets < 0 or reps < 0:
            return jsonify({"error": "Підходи та повтори не можуть бути від'ємними"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Поля target_sets, sets та reps мають бути цілими числами"}), 400

    # 4. Перевірка текстових полів на порожнечу
    date = str(data["date"]).strip()
    exercise = str(data["exercise"]).strip()
    
    if not date or not exercise:
        return jsonify({"error": "Поля date та exercise не можуть бути порожніми"}), 400

    # Якщо всі 4 етапи перевірки пройдено — зберігаємо в БД
    note = str(data.get("note", "")).strip()
    new_id = storage.add(date, exercise, target_sets, sets, reps, note)
    
    return jsonify({"id": new_id, "message": "Запис успішно додано"}), 201

@app.delete("/items/<int:item_id>")
def delete_item(item_id):
    if storage.delete(item_id):
        return jsonify({"deleted": item_id})
    return jsonify({"error": f"Запис з ID {item_id} не знайдено"}), 404

@app.get("/report")
def report():
    return jsonify(logic.total_stats_by_exercise(storage.load()))

if __name__ == "__main__":
    app.run(debug=True)