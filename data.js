const plantsData = [
    { 
        name: "Лимоны / Цитрусы", 
        waterFreq: 1, 
        feedMonths: [2, 5, 7], 
        feedNote: "N-формула (2:1:1), только если есть рост",
        pruneMonths: [0,1,2,3,4,5,6,7,8,9,10,11],
        pruneNote: "Удалять побеги ниже прививки",
        warning: "Влажность 25% критична! Цель — 50% RH."
    },
    { 
        name: "Адениум", 
        waterFreq: 21, 
        feedMonths: [4, 5, 6, 7], 
        feedNote: "Низкий N, высокий P-K, 1/4 дозы",
        pruneMonths: [2, 3],
        pruneNote: "Весенняя формировка. Стерильный нож!",
        repotMonths: [3, 4],
        warning: "Ядовитый сок! Не резать без яркого света."
    },
    { 
        name: "Кактусы (Взрослые)", 
        waterFreq: 21, 
        feedMonths: [4, 6], 
        feedNote: "Удобрение для суккулентов, 1/2 нормы",
        repotMonths: [3], 
        repotNote: "Апрель: пауза 3-5 дней до полива",
        warning: "Нужен 'wet-dry cycle' (полная просушка)."
    },
    { 
        name: "Кактусы (Сеянцы)", 
        waterFreq: 3, 
        feedMonths: [2,3,4,5,6,7,8], 
        feedNote: "1/4 силы 20-20-20 раз в неделю (при >1.3см)",
        repotMonths: [2, 3], 
        repotNote: "Пикировка при диаметре >1.3см",
        warning: "Не допускать полной засухи!"
    },
    { 
        name: "Орхидея Фаленопсис", 
        waterFreq: 7, 
        feedMonths: [2,3,4,5,6,7,8,9], 
        feedNote: "Каждый 3-й полив, зимой — пропуск",
        pruneMonths: [5, 6],
        pruneNote: "Срез над 2-м узлом после цветения",
        warning: "RH 25% — риск клеща. Опрыскивать зону вокруг."
    },
    { 
        name: "Фиалки", 
        waterFreq: 7, 
        feedMonths: [0,1,2,3,4,5,6,7,8,9,10,11], 
        feedNote: "1/4 нормы при каждом поливе",
        warning: "Промывать субстрат от солей раз в месяц."
    },
    { 
        name: "Гранат комнатный",
        waterFreq: 4,
        feedMonths: [2, 3, 4, 5, 6, 7],
        feedNote: "Умеренно, при активном росте",
        warning: "Очень светолюбив (место B)!"
    },
    { 
        name: "Каланхоэ", 
        waterFreq: 7,
        feedMonths: [4, 5, 6, 7, 8],
        pruneMonths: [5], 
        warning: "Октябрь: режим короткого дня для бутонов."
    }
];
