# tools/generate_data_js.py
import json

def generate():
    with open("plants.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("/* data.js — автоматически сгенерировано из plants.json */\n\n")
        # careCalendar можно оставить как константу или тоже перенести
        f.write('const careCalendar = ' + json.dumps(careCalendar_example, ensure_ascii=False, indent=2) + ";\n\n")  # вставь свой careCalendar сюда
        f.write('const plantsData = ' + json.dumps(data["plants"], ensure_ascii=False, indent=2) + ";\n")
    print("✅ data.js обновлён!")

if __name__ == "__main__":
    # вставь сюда свой careCalendar из старого data.js
    careCalendar_example = [...]  # твой оригинальный массив
    generate()
