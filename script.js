function showView(viewName) {
    document.querySelectorAll('.view-section').forEach(v => v.style.display = 'none');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('view-' + viewName).style.display = 'block';
    document.getElementById('btn-' + viewName).classList.add('active');
    
    if (viewName === 'collection') { renderStats(); renderCollection(); }
    if (viewName === 'year') renderYearView();
}

function renderStats() {
    const d = new Date().getDate();
    const total = plantsData.length;
    const toWater = plantsData.filter(p => p.waterFreq === 1 || d % p.waterFreq === 0).length;
    const statsHTML = `
        <div class="stats-container">
            <div class="stat-card"><span class="stat-value">${total}</span><span class="stat-label">В составе</span></div>
            <div class="stat-card blue"><span class="stat-value">${toWater}</span><span class="stat-label">Полить сегодня</span></div>
        </div>`;
    document.getElementById('collectionList').innerHTML = statsHTML;
}

function renderCollection() {
    const list = document.getElementById('collectionList');
    plantsData.forEach(p => {
        const lastLog = p.history && p.history.length > 0 ? p.history[p.history.length - 1] : { date: "-", event: "Нет записей" };
        list.innerHTML += `
            <div class="plant-card">
                <h3>${p.name} <span class="category-tag">${p.category}</span></h3>
                <div class="info-item"><b>📍 Место:</b> ${p.location}</div>
                <div class="info-item"><b>💧 Полив:</b> ${p.waterFreq === 1 ? 'ежедневно' : 'раз в ' + p.waterFreq + ' дн.'}</div>
                <div class="history-box"><b>Последнее:</b> ${lastLog.date} — ${lastLog.event}</div>
            </div>`;
    });
}

function renderYearView() {
    const monthsShort = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    const currentMonth = new Date().getMonth();
    const header = document.getElementById('tableHeader');
    header.innerHTML = '<th>Растение</th>' + monthsShort.map((m, i) => `<th class="${i === currentMonth ? 'current-month-col' : ''}">${m}</th>`).join('');

    const body = document.getElementById('tableBody');
    body.innerHTML = "";
    plantsData.forEach(p => {
        let row = `<tr><td>${p.name}</td>`;
        for (let m = 0; m < 12; m++) {
            let icons = ""; let isActive = false;
            if (p.feedMonths && p.feedMonths.includes(m)) { icons += "💊"; isActive = true; }
            if (p.pruneMonths && p.pruneMonths.includes(m)) { icons += "✂️"; isActive = true; }
            if (p.repotMonths && p.repotMonths.includes(m)) { icons += "🪴"; isActive = true; }
            row += `<td class="${isActive ? 'cell-active' : ''} ${m === currentMonth ? 'current-month-col' : ''}">${icons}</td>`;
        }
        body.innerHTML += row + "</tr>";
    });
}

function updateCalendar() {
    const now = new Date(); const d = now.getDate(); const m = now.getMonth();
    const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    document.getElementById('monthName').innerText = months[m];
    document.getElementById('yearNum').innerText = now.getFullYear();
    document.getElementById('dayNum').innerText = d;
    document.getElementById('dayName').innerText = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'][now.getDay()];

    let tasks = "";
    plantsData.forEach(p => {
        if (p.waterFreq === 1 || d % p.waterFreq === 0) {
            tasks += `<div style="text-align:left; margin-bottom:8px;">✅ <b>${p.name}:</b> Полив</div>`;
            if (p.feedMonths && p.feedMonths.includes(m) && (p.waterFreq > 1 || d === 1 || d === 15)) {
                tasks += `<div style="text-align:left; color: #d35400; margin-bottom:12px; padding-left: 20px; font-size: 13px;">🧪 ${p.feedNote || 'Подкормка'}</div>`;
            }
        }
        if (d <= 5) {
            if (p.repotMonths && p.repotMonths.includes(m)) tasks += `<div style="text-align:left; color: #27ae60; font-size: 13px;">🪴 <b>${p.name}:</b> План пересадки</div>`;
            if (p.pruneMonths && p.pruneMonths.includes(m)) tasks += `<div style="text-align:left; color: #2980b9; font-size: 13px;">✂️ <b>${p.name}:</b> План обрезки</div>`;
        }
    });
    document.getElementById('todayTasks').innerHTML = tasks || "Сегодня по плану отдых 🌿";
}

updateCalendar();
