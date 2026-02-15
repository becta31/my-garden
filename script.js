function showView(viewName) {
  document.querySelectorAll('.view-section').forEach(v => v.style.display = 'none');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  document.getElementById('view-' + viewName).style.display = 'block';
  document.getElementById('btn-' + viewName).classList.add('active');

  if (viewName === 'collection') renderCollection();
  if (viewName === 'year') renderYearView();
  if (viewName === 'today') updateCalendar();
}

// ================= COLLECTION =================
function renderCollection() {
  const list = document.getElementById('collectionList');
  if (!list) return;

  const d = new Date().getDate();
  const total = plantsData.length;
  const toWater = plantsData.filter(p => p.waterFreq === 1 || d % p.waterFreq === 0).length;

  list.innerHTML = `
    <div class="stats-container">
      <div class="stat-card">
        <span class="stat-value">${total}</span>
        <span class="stat-label">В составе</span>
      </div>
      <div class="stat-card blue">
        <span class="stat-value">${toWater}</span>
        <span class="stat-label">Полить сегодня</span>
      </div>
    </div>
  `;

  plantsData.forEach(p => {
    const lastLog = p.history && p.history.length > 0
      ? p.history[p.history.length - 1]
      : { date: "-", event: "Нет записей" };

    list.innerHTML += `
      <div class="plant-card">
        <h3>${p.name} <span class="category-tag">${p.category}</span></h3>
        <div class="info-item"><b>📍 Место:</b> ${p.location || 'Не указано'}</div>
        <div class="info-item"><b>💧 Полив:</b> ${p.waterFreq === 1 ? 'ежедневно' : 'раз в ' + p.waterFreq + ' дн.'}</div>
        <div class="history-box"><b>Последнее:</b> ${lastLog.date} — ${lastLog.event}</div>
      </div>
    `;
  });
}

// ================= YEAR =================
function renderYearView() {
  const monthsShort = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
  const currentMonth = new Date().getMonth();
  const header = document.getElementById('tableHeader');
  const body = document.getElementById('tableBody');

  header.innerHTML =
    '<th>Растение</th>' +
    monthsShort.map((m, i) =>
      `<th class="${i === currentMonth ? 'current-month-col' : ''}">${m}</th>`
    ).join('');

  body.innerHTML = "";

  plantsData.forEach(p => {
    let row = `<tr><td>${p.name}</td>`;

    for (let m = 0; m < 12; m++) {
      let icons = "";
      let isActive = false;

      if (p.feedMonths && p.feedMonths.includes(m)) { icons += "💊"; isActive = true; }
      if (p.pruneMonths && p.pruneMonths.includes(m)) { icons += "✂️"; isActive = true; }
      if (p.repotMonths && p.repotMonths.includes(m)) { icons += "🪴"; isActive = true; }

      row += `<td class="${isActive ? 'cell-active' : ''} ${m === currentMonth ? 'current-month-col' : ''}">${icons}</td>`;
    }

    body.innerHTML += row + "</tr>";
  });
}

// ================= HELPERS =================

// логика как в боте
function hasFeedToday(p, month, day) {
  if (!p.feedMonths || !p.feedMonths.includes(month)) return false;

  // та же логика что в Python
  if (p.waterFreq > 1) return true;
  if (day === 1 || day === 15) return true;

  return false;
}

// ================= TODAY =================
function updateCalendar() {
  const now = new Date();
  const d = now.getDate();
  const m = now.getMonth();

  const months = [
    'Январь','Февраль','Март','Апрель','Май','Июнь',
    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'
  ];

  document.getElementById('monthName').innerText = months[m];
  document.getElementById('yearNum').innerText = now.getFullYear();
  document.getElementById('dayNum').innerText = d;
  document.getElementById('dayName').innerText =
    ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'][now.getDay()];

  const container = document.getElementById('todayTasks');
  if (!container) return;

  let html = "";
  let hasTasks = false;

  plantsData.forEach(p => {
    const needWater = p.waterFreq === 1 || d % p.waterFreq === 0;
    if (!needWater) return;

    hasTasks = true;

    const needFeed = hasFeedToday(p, m, d);
    const freqText = p.waterFreq === 1 ? 'ежедневно' : `раз в ${p.waterFreq} дн.`;

    html += `
      <div class="task-card">

        <div class="task-head">
          <div class="task-plant">${p.name}</div>
          <div class="task-meta">${freqText}</div>
        </div>

        <div class="task-actions">
          <span class="chip">💧 Полить</span>
          ${needFeed ? `<span class="chip secondary">🧪 Подкормить</span>` : ``}
        </div>

        ${needFeed && p.feedShort ? `
          <div class="task-note">💊 ${p.feedShort}</div>
        ` : ``}

      </div>
    `;
  });

  container.innerHTML = hasTasks
    ? html
    : `
      <div class="empty-state">
        <div class="empty-emoji">🌿</div>
        <div class="empty-title">Сегодня отдых</div>
        <div class="empty-text">Полив не требуется</div>
      </div>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
  updateCalendar();
});
