const plants = [
    { name: "Лимоны", task: "Полив + Опрыскивание", freq: 1 },
    { name: "Орхидея / Фиалки", task: "Полив", freq: 7 },
    { name: "Замиокулькас / Нолина", task: "Проверка грунта", freq: 14 },
    { name: "Адениум / Кактусы", task: "Скудный полив", freq: 21 }
];

function updateCalendar() {
    const now = new Date();
    const d = now.getDate();
    const month = now.toLocaleString('ru', { month: 'long' }).toUpperCase();
    const weekday = now.toLocaleString('ru', { weekday: 'long' });

    document.getElementById('monthName').innerText = month;
    document.getElementById('dayNum').innerText = d;
    document.getElementById('dayName').innerText = weekday;

    if (now.getDay() === 0) {
        document.getElementById('sheet').classList.add('is-sunday');
    }

    let html = '';
    plants.forEach(p => {
        if (p.freq === 1 || d % p.freq === 0) {
            html += `<div class="plant-task">🌿 ${p.name}: ${p.task}</div>`;
        }
    });

    document.getElementById('taskList').innerHTML = html || "Сегодня только отдых 🌿";
}

updateCalendar();
