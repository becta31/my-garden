// ================= VIEW SWITCH =================
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
  const toWater = plantsData.filter(p => {
    const wf = Number(p.waterFreq || 99);
    return wf === 1 || d % wf === 0;
  }).length;

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
    const lastLog = (p.history && p.history.length > 0)
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


// ================= YEAR VIEW =================
function renderYearView() {
  const monthsShort = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
  const currentMonth = new Date().getMonth();

  const header = document.getElementById('tableHeader');
  const body = document.getElementById('tableBody');
  if (!header || !body) return;

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

      if (p.feedMonths && p.feedMonths.includes(m)) {
        icons += "💊";
        isActive = true;
      }
      if (p.pruneMonths && p.pruneMonths.includes(m)) {
        icons += "✂️";
        isActive = true;
      }
      if (p.repotMonths && p.repotMonths.includes(m)) {
        icons += "🪴";
        isActive = true;
      }

      row += `<td class="${isActive ? 'cell-active' : ''} ${m === currentMonth ? 'current-month-col' : ''}">${icons}</td>`;
    }

    body.innerHTML += row + "</tr>";
  });
}


// ================= TODAY HELPERS =================
function hasFeedToday(p, month, day) {
  if (!p.feedMonths || !p.feedMonths.includes(month)) return false;
  const wf = Number(p.waterFreq || 99);
  return (wf > 1) || (day === 1 || day === 15);
}

function pickFeedText(p) {
  return (p.feedShort && String(p.feedShort).trim())
    ? p.feedShort
    : (p.feedNote || "");
}


// ================= TODAY VIEW =================
function updateCalendar() {
  const now = new Date();
  const d = now.getDate();
  const m = now.getMonth();

  const months = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const weekdays = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];

  document.getElementById('monthName').innerText = months[m];
  document.getElementById('yearNum').innerText = now.getFullYear();
  document.getElementById('dayNum').innerText = d;
  document.getElementById('dayName').innerText = weekdays[now.getDay()];

  const todayBox = document.getElementById('todayTasks');
  if (!todayBox) return;

  let html = "";
  let count = 0;

  // ===== ОСНОВНЫЕ ЗАДАЧИ =====
  plantsData.forEach(p => {
    const wf = Number(p.waterFreq || 99);
    const waterToday = (wf === 1) || (d % wf === 0);
    if (!waterToday) return;

    count++;

    const feedToday = hasFeedToday(p, m, d);
    const loc = p.location || "";
    const stage = p.stage || "";
    const warn = p.warning || "";

    const chips = [
      `<span class="chip">💧 Полить</span>`,
      feedToday ? `<span class="chip secondary">🧪 Подкормить</span>` : ''
    ].join("");

    let noteBlock = "";
    if (feedToday) {
      const text = pickFeedText(p).trim();
      if (text) {
        noteBlock = `<div class="task-note"><b>Формула:</b> ${text}</div>`;
      }
    }

    let hints = "";
    if (stage) hints += `<div class="task-hint">🔎 Режим: <b>${stage}</b></div>`;
    if (warn) hints += `<div class="task-hint warn">⚠️ ${warn}</div>`;
    if (hints) hints = `<div class="task-hints">${hints}</div>`;

    html += `
      <div class="task-card">
        <div class="task-head">
          <div class="task-plant">${String(p.name).toUpperCase()}</div>
          <div class="task-meta">${loc}</div>
        </div>

        <div class="task-actions">${chips}</div>

        ${noteBlock}
        ${hints}
      </div>
    `;
  });

  // ===== ПЛАНЫ ДО 5 ЧИСЛА =====
  if (d <= 5) {
    plantsData.forEach(p => {
      let planIcons = [];
      if (p.repotMonths && p.repotMonths.includes(m)) planIcons.push("🪴 Пересадка");
      if (p.pruneMonths && p.pruneMonths.includes(m)) planIcons.push("✂️ Обрезка");
      if (!planIcons.length) return;

      html += `
        <div class="task-card plan-card">
          <div class="task-head">
            <div class="task-plant">${String(p.name).toUpperCase()}</div>
            <div class="task-meta">План (до 5 числа)</div>
          </div>
          <div class="task-actions">
            ${planIcons.map(t => `<span class="chip warn">${t}</span>`).join("")}
          </div>
        </div>
      `;
    });
  }

  // ===== EMPTY =====
  if (!count && !html.trim()) {
    todayBox.innerHTML = `
      <div class="empty-state">
        <div class="empty-emoji">🌿</div>
        <div class="empty-title">Сегодня отдых</div>
        <div class="empty-text">По расписанию нет полива и действий</div>
      </div>
    `;
  } else {
    todayBox.innerHTML = html;
  }
}


// ================= INIT =================
document.addEventListener('DOMContentLoaded', () => {
  updateCalendar();
});
