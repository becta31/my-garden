function updateCalendar() {
    const now = new Date();
    const d = now.getDate();
    const m = now.getMonth(); // 0 = Январь
    const y = now.getFullYear();

    // 1. Установка даты в шапке
    const monthsNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    const daysNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];

    document.getElementById('monthName').innerText = monthsNames[m];
    document.getElementById('yearNum').innerText = y;
    document.getElementById('dayNum').innerText = d;
    document.getElementById('dayName').innerText = daysNames[now.getDay()];

    // Красим воскресенье
    if (now.getDay() === 0) document.getElementById('sheet').classList.add('is-holiday');
    else document.getElementById('sheet').classList.remove('is-holiday');

    // 2. Обработка списка растений из data.js
    let tasksHTML = "";
    let seasonalAdviceHTML = "";

    // plantsData берется из подключенного файла data.js
    plantsData.forEach(p => {
        let plantActions = [];

        // --- ЛОГИКА ПОЛИВА ---
        // Если частота 1 (каждый день) ИЛИ сегодня день полива по графику
        if (p.waterFreq === 1 || d % p.waterFreq === 0) {
            plantActions.push(`<span class="tag">💧</span>Полив / Осмотр`);
            
            // --- ЛОГИКА УДОБРЕНИЯ ---
            // Удобряем только в день полива И если текущий месяц есть в списке "месяцев кормежки"
            if (p.feedMonths && p.feedMonths.includes(m)) {
                // Доп. фильтр: не удобрять каждый день (для лимонов) - только 1-го и 15-го числа
                if (p.waterFreq === 1 && d !== 1 && d !== 15) {
                    // пропускаем
                } else {
                    plantActions.push(`<span class="tag">💊</span>Подкормка: ${p.feedNote}`);
                }
            }
        }

        // --- ЛОГИКА ПЕРЕСАДКИ (Напоминание с 1 по 3 число месяца) ---
        if (p.repotMonths && p.repotMonths.includes(m) && d <= 3) {
            plantActions.push(`<span class="tag">🪴</span>ПЛАН: ${p.repotNote || 'Пересадка'}`);
        }

        // --- ЛОГИКА ОБРЕЗКИ (Напоминание с 5 по 7 число месяца) ---
        if (p.pruneMonths && p.pruneMonths.includes(m) && d >= 5 && d <= 7) {
            plantActions.push(`<span class="tag">✂️</span>ПЛАН: ${p.pruneNote || 'Обрезка'}`);
        }

        // Если есть действия, добавляем строку в HTML
        if (plantActions.length > 0) {
            tasksHTML += `<div class="task-row"><strong>${p.name}:</strong><br>${plantActions.join('<br>')}</div>`;
        }

        // --- СБОР СОВЕТОВ (ПРЕДУПРЕЖДЕНИЯ) ---
        // Показываем предупреждение, если оно критично для текущего месяца
        if (p.warning) {
            // Для Цитрусов и Орхидей зимой (месяцы 0, 1, 10, 11) напоминаем про влажность
            if ((m <= 1 || m >= 10) && (p.name.includes("Лимон") || p.name.includes("Орхидея"))) {
                seasonalAdviceHTML = `⚠️ <b>Зима (${p.name}):</b> ${p.warning}`;
            }
            // Для Адениума весной (месяц 2, 3) напоминаем про обрезку
            if ((m === 2 || m === 3) && p.name.includes("Адениум")) {
                seasonalAdviceHTML = `ℹ️ <b>Весна (${p.name}):</b> ${p.pruneNote}`;
            }
            // Для Каланхоэ в октябре (месяц 9)
            if (m === 9 && p.name.includes("Каланхоэ")) {
                seasonalAdviceHTML = `🍂 <b>Октябрь:</b> ${p.warning}`;
            }
        }
    });

    // Вывод задач
    document.getElementById('todayTasks').innerHTML = tasksHTML || "Сегодня плановых работ нет 🌿";

    // Вывод советов
    if (seasonalAdviceHTML) {
        document.getElementById('seasonalBlock').style.display = 'block';
        document.getElementById('seasonalAdvice').innerHTML = seasonalAdviceHTML;
    } else {
        document.getElementById('seasonalBlock').style.display = 'none';
    }

    // 3. Прогноз на завтра (просто для инфо)
    const tomorrow = d + 1;
    document.getElementById('nextTaskInfo').innerHTML = `Завтра (${tomorrow}-го) проверим влажность и освещение.`;
}

// Запуск
updateCalendar();

// Обновление каждый час
setInterval(updateCalendar, 3600000);
