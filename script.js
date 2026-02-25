// script.js — отметки "Сделано" (localStorage) + Today cards + Collection + Year

// ---------- helpers ----------
function todayKey() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function plantKey(p) {
  // если нет id — используем имя
  return (p && p.id) ? String(p.id) : String(p?.name || "unknown");
}

function getDoneMap() {
  // структура:
  // { "2026-02-15": { "adenium-young": { water:true, feed:false } } }
  try {
    return JSON.parse(localStorage.getItem("garden_done_v1") || "{}");
  } catch (e) {
    return {};
  }
}

function setDoneMap(map) {
  localStorage.setItem("garden_done_v1", JSON.stringify(map));
}

function getDoneForToday(plantId) {
  const map = getDoneMap();
  const day = todayKey();
  return (map[day] && map[day][plantId]) ? map[day][plantId] : { water: false, feed: false };
}

function setDoneForToday(plantId, patch) {
  const map = getDoneMap();
  const day = todayKey();
  map[day] = map[day] || {};
  const cur = map[day][plantId] || { water: false, feed: false };
  map[day][plantId] = { ...cur, ...patch };
  setDoneMap(map);
}

function clearDoneForToday() {
  const map = getDoneMap();
  const day = todayKey();
  delete map[day];
  setDoneMap(map);
}

// ---------- navigation ----------
function showView(viewName) {
  document.querySelectorAll(".view-section").forEach(v => v.style.display = "none");
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  const view = document.getElementById("view-" + viewName);
  const btn = document.getElementById("btn-" + viewName);
  if (view) view.style.display = "block";
  if (btn) btn.classList.add("active");

  if (viewName === "collection") renderCollection();
  if (viewName === "year") renderYearView();
  if (viewName === "today") updateCalendar();
}

// ---------- collection ----------
function renderCollection() {
  const list = document.getElementById("collectionList");
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
        <div class="info-item"><b>📍 Место:</b> ${p.location || "Не указано"}</div>
        <div class="info-item"><b>💧 Полив:</b> ${p.waterFreq === 1 ? "ежедневно" : "раз в " + p.waterFreq + " дн."}</div>
        <div class="history-box"><b>Последнее:</b> ${lastLog.date} — ${lastLog.event}</div>
      </div>
    `;
  });
}

// ---------- year view ----------
function renderYearView() {
  const monthsShort = ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];
  const currentMonth = new Date().getMonth();
  const header = document.getElementById("tableHeader");
  const body = document.getElementById("tableBody");
  if (!header || !body) return;

  header.innerHTML =
    "<th>Растение</th>" +
    monthsShort.map((m, i) => `<th class="${i === currentMonth ? "current-month-col" : ""}">${m}</th>`).join("");

  body.innerHTML = "";

  plantsData.forEach(p => {
    let row = `<tr><td>${p.name}</td>`;
    for (let m = 0; m < 12; m++) {
      let icons = "";
      let isActive = false;
      if (p.feedMonths && p.feedMonths.includes(m)) { icons += "💊"; isActive = true; }
      if (p.pruneMonths && p.pruneMonths.includes(m)) { icons += "✂️"; isActive = true; }
      if (p.repotMonths && p.repotMonths.includes(m)) { icons += "🪴"; isActive = true; }
      row += `<td class="${isActive ? "cell-active" : ""} ${m === currentMonth ? "current-month-col" : ""}">${icons}</td>`;
    }
    body.innerHTML += row + "</tr>";
  });
}

// ---------- today (planner) ----------
function updateCalendar() {
  const now = new Date();
  const d = now.getDate();
  const m = now.getMonth();

  const months = [
    "Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"
  ];

  const monthEl = document.getElementById("monthName");
  const yearEl = document.getElementById("yearNum");
  const dayEl = document.getElementById("dayNum");
  const dayNameEl = document.getElementById("dayName");

  if (monthEl) monthEl.innerText = months[m];
  if (yearEl) yearEl.innerText = now.getFullYear();
  if (dayEl) dayEl.innerText = d;
  if (dayNameEl) dayNameEl.innerText =
    ["Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота"][now.getDay()];

  const container = document.getElementById("todayTasks");
  if (!container) return;

  let html = "";
  let hasTasks = false;

  // верхняя панель: сброс отметок
  html += `
    <div class="today-toolbar">
      <button class="mini-btn" type="button" id="btnClearToday">Сбросить отметки на сегодня</button>
    </div>
  `;

  plantsData.forEach(p => {
    const needWater = (p.waterFreq === 1) || (d % p.waterFreq === 0);
    if (!needWater) return;

    hasTasks = true;

    const needFeed = (p.feedMonths && p.feedMonths.includes(m));
    const freqText = p.waterFreq === 1 ? "ежедневно" : `раз в ${p.waterFreq} дн.`;
    const pid = plantKey(p);

    const done = getDoneForToday(pid);
    const waterDone = !!done.water;
    const feedDone = !!done.feed;

    const cardDone = (needFeed ? (waterDone && feedDone) : waterDone);

    html += `
      <div class="task-card ${cardDone ? "done-card" : ""}" data-plant="${pid}">
        <div class="task-head">
          <div class="task-plant">${p.name}</div>
          <div class="task-meta">${freqText}</div>
        </div>

        <div class="task-actions">
          <button class="chip-btn ${waterDone ? "done" : ""}" type="button" data-action="water">
            💧 Полить
          </button>

          ${needFeed ? `
            <button class="chip-btn secondary ${feedDone ? "done" : ""}" type="button" data-action="feed">
              🧪 Подкормить
            </button>
          ` : ``}
        </div>

        ${needFeed && (p.feedShort || p.feedNote) ? `
          <div class="task-note">💊 ${(p.feedShort || p.feedNote)}</div>
        ` : ``}

        ${p.warning ? `
          <div class="task-warn">⚠️ ${p.warning}</div>
        ` : ``}
      </div>
    `;
  });

  if (!hasTasks) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-emoji">🌿</div>
        <div class="empty-title">Сегодня отдых</div>
        <div class="empty-text">Полив не требуется</div>
      </div>
    `;
    return;
  }

  container.innerHTML = html;

  // handlers
  const btnClear = document.getElementById("btnClearToday");
  if (btnClear) {
    btnClear.onclick = () => {
      clearDoneForToday();
      updateCalendar();
    };
  }

  container.querySelectorAll(".chip-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".task-card");
      if (!card) return;
      const pid = card.getAttribute("data-plant");
      const action = btn.getAttribute("data-action");

      const done = getDoneForToday(pid);
      if (action === "water") setDoneForToday(pid, { water: !done.water });
      if (action === "feed") setDoneForToday(pid, { feed: !done.feed });

      updateCalendar();
    });
  });
}

// старт
document.addEventListener("DOMContentLoaded", () => {
  updateCalendar();
});
