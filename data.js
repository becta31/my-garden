/* ПОЛНАЯ БАЗА РАСТЕНИЙ (версия 2026: NPK Edition)
   Месяцы: 0=Янв, 1=Фев, 2=Мар, 3=Апр, 4=Май, 5=Июн, 
          6=Июл, 7=Авг, 8=Сен, 9=Окт, 10=Ноя, 11=Дек
*/

const plantsData = [
    { 
        "id": "citrus-group",
        "name": "Лимоны / Цитрусы", 
        "category": "fruit",
        "location": "Окно (Оптимально СВ)",
        "light": "Яркий/Средний",
        "waterFreq": 1, 
        "feedMonths": [2, 3, 4, 5, 6, 7], 
        "feedNote": "1г NPK 20-10-20 (или 5мл жидкого «Для Цитрусов»)",
        "pruneMonths": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 
        "warning": "Влажность 25% — риск листопада! Цель: 50%.",
        "history": [{ "date": "2026-02-10", "event": "Мониторинг", "note": "Зимнее содержание." }]
    },
    { 
        "id": "adenium-young",
        "name": "Адениум (Молодой)", 
        "category": "adenium",
        "location": "Юго-Запад (Полка B + Лампа)",
        "light": "Максимальный (подсветка)",
        "waterFreq": 14, 
        "feedMonths": [4, 5, 6, 7], 
        "feedNote": "0.5г NPK 10-50-10 (Взрыватель цветения/корней)",
        "repotMonths": [3, 4],
        "pruneMonths": [2, 3],
        "warning": "ЯДОВИТЫЙ СОК! Обрезка только в перчатках.",
        "history": [{ "date": "2026-01-20", "event": "Подготовка", "note": "Ждем марта." }]
    },
    { 
        "id": "cactus-adult",
        "name": "Кактусы (Взрослые)", 
        "category": "cactus",
        "location": "Юго-Запад (Полка B)",
        "light": "Яркий прямой",
        "waterFreq": 21, 
        "feedMonths": [4, 6], 
        "feedNote": "2мл жидкого «Для кактусов» (низкий Азот)",
        "repotMonths": [3],
        "warning": "Wet-dry cycle: полная просушка между поливами.",
        "history": [{ "date": "2026-02-01", "event": "Покой", "note": "Зимовка." }]
    },
    { 
        "id": "cactus-seeds",
        "name": "Кактусы (Сеянцы)", 
        "category": "cactus",
        "location": "Юго-Запад (Полка B + Лампа)",
        "light": "Яркий рассеянный",
        "waterFreq": 3, 
        "feedMonths": [2, 3, 4, 5, 6, 7, 8], 
        "feedNote": "0.2г NPK 20-20-20 (на кончике ножа / микродоза)",
        "repotMonths": [2, 3],
        "repotNote": "Пикировка при диаметре >1.3см",
        "warning": "Не допускать полной засухи как у взрослых!",
        "history": [{ "date": "2026-01-23", "event": "Практика", "note": "Молодые игроки в составе." }]
    },
    { 
        "id": "orchids-violets",
        "name": "Орхидеи / Фиалки", 
        "category": "flower",
        "location": "Светлое место",
        "light": "Мягкий свет",
        "waterFreq": 7, 
        "feedMonths": [2, 3, 4, 5, 6, 7, 8, 9], 
        "feedNote": "1мл жидкого «Бона Форте» (или NPK 18-18-18)",
        "warning": "Орхидеи: RH 25% — риск клеща! Опрыскивать вокруг.",
        "history": []
    },
    { 
        "id": "pomegranate-mini",
        "name": "Гранат комнатный",
        "category": "fruit",
        "location": "Юго-Запад (Полка B)",
        "light": "Очень яркий",
        "waterFreq": 4,
        "feedMonths": [2, 3, 4, 5, 6, 7],
        "feedNote": "1г NPK 20-20-20 (Универсальное)",
        "warning": "Листопадное! Зимой может сбросить часть листвы. В марте — обрезка.",
        "history": []
    },
    { 
        "id": "kalanchoe",
        "name": "Каланхоэ", 
        "category": "succulent",
        "location": "Подоконник",
        "light": "Яркий",
        "waterFreq": 7, 
        "feedMonths": [4, 5, 6, 7, 8],
        "feedNote": "2мл жидкого для суккулентов",
        "pruneMonths": [5], 
        "warning": "Октябрь: режим короткого дня для цветения.",
        "history": []
    },
    { 
        "id": "gloxinia",
        "name": "Глоксиния", 
        "category": "flower",
        "location": "Полка",
        "light": "Рассеянный",
        "waterFreq": 7, 
        "feedMonths": [3, 4, 5, 6, 7],
        "feedNote": "1г NPK 10-50-10 (для закладки бутонов)",
        "warning": "Зимой клубень спит.",
        "history": []
    }
];
