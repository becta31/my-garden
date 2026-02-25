// script.js (Today cards UI + history.json support + safe rendering)

let historyIndex = {}; // { plantId: [ {date,event,note}... ] }

/** Безопасно экранируем текст для HTML */
function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/** Читаем историю из history.json (и не даём SW/браузеру закэшировать) */
async function loadHistory() {
  try {
    const res = await fetch(`history.json?ts=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`history.json HTTP ${res.status}`);
    const data = await res.json();

    const idx = {};
    const entries = Array.isArray(data.entries) ? data.entries : [];

    for (const e of entries) {
      const id = e.id || e.plantId;
      if (!id) continue;
      if (!idx[id]) idx[id] = [];
      idx[id].push({
        date: e.date || "-",
        event: e.event || "Запись",
        note: e.note || ""
      });
    }

    // сортировка по дате (если ISO), иначе как есть
    for (const id of Object.keys(idx)) {
      idx[id].sort((a, b) => String(a.date).localeCompare(String(b.date)));
    }

    historyIndex = idx;
  } catch (err) {
    console.log("History load failed:", err);
    historyIndex = {};
  }
}

/** Берём последнюю запись: сначала из history.json, иначе из data.js (p.history) */
function getLastLog(p) {
  const fromJson = historyIndex[p.id];
  if (fromJson && fromJson.length) return fromJson[fromJson.length - 1];

  const h = p.history;
  if (Array.isArray(h) && h.length) return h[h.length - 1];

  return null;
}

function showView(viewName) {
  document.querySelectorAll(".view-section").forEach(v => (v.style.display = "none"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  const viewEl = document.getElementById("view-" + viewName);
  const btnEl = document.getElementById("btn-" + viewName);
  if (viewEl) viewEl.style.display = "block";
  if (btnEl) btnEl.classList.add("active");

  if (viewName === "collection") renderCollection();
  if (viewName === "year") renderYearView();
  if (viewName === "today") updateCalendar();
}

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
    const last = getLastLog(p);
    const lastText = last
      ? `${escapeHtml(last.date)} — ${escapeHtml(last.event)}${last.note ? ` (${escapeHtml(last.note)})` : ""}`
      : `—`;

    list.innerHTML += `
      <div class="plant-card">
        <h3>${escapeHtml(p.name)} <span class="category-tag">${escapeHtml(p.category || "")}</span></h3>
        <div class="info-item"><b>📍 Место:</b> ${escapeHtml(p.location || "Не указано")}</div>
        <div class="info-item"><b>💧 Полив:</b> ${p.waterFreq === 1 ? "ежедневно" : "раз в " + escapeHtml(p.waterFreq) + " дн."}</div>
        <div class="history-box"><b>Последнее:</b> ${lastText || "Нет записей"}</div>
      </div>
    `;
  });
}

function renderYearView() {
  const monthsShort = ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];
  const currentMonth = new Date().getMonth();
  const header = document.getElementById("tableHeader");
  const body = document.getElementById("tableBody");
  if (!header || !body) return;

  header.innerHTML =
    "<th>Растение</th>" +
    monthsShort
      .map((m, i) => `<th class="${i === currentMonth ? "current-month-col" : ""}">${m}</th>`)
      .join("");

  body.innerHTML = "";

  plantsData.forEach(p => {
    let row = `<tr><td>${escapeHtml(p.name)}</td>`;

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

function updateCalendar() {
  const now = new Date();
  const d = now.getDate();
  const m = now.getMonth();

  const months = [
    "Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"
  ];

  const monthName = document.getElementById("monthName");
  const yearNum = document.getElementById("yearNum");
  const dayNum = document.getElementById("dayNum");
  const dayName = document.getElementById("dayName");
  const container = document.getElementById("todayTasks");

  if (monthName) monthName.innerText = months[m];
  if (yearNum) yearNum.innerText = now.getFullYear();
  if (dayNum) dayNum.innerText = d;
  if (dayName) dayName.innerText = ["Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота"][now.getDay()];
  if (!container) return;

  let html = "";
  let hasTasks = false;

  plantsData.forEach(p => {
    const needWater = p.waterFreq === 1 || d % p.waterFreq === 0;
    if (!needWater) return;

    hasTasks = true;

    // Подкормка показывается только как "в этом месяце" (как у тебя было)
    const needFeed = p.feedMonths && p.feedMonths.includes(m);
    const freqText = p.waterFreq === 1 ? "ежедневно" : `раз в ${p.waterFreq} дн.`;

    const note = needFeed ? (p.feedShort || p.feedNote || "") : "";
    const warn = p.warning || "";

    html += `
      <div class="task-card">
        <div class="task-head">
          <div class="task-plant">${escapeHtml(p.name)}</div>
          <div class="task-meta">${escapeHtml(freqText)}</div>
        </div>

        <div class="task-actions">
          <span class="chip">💧 Полить</span>
          ${needFeed ? `<span class="chip secondary">🧪 Подкормить</span>` : ``}
          ${warn ? `<span class="chip warn">⚠️ Важно</span>` : ``}
        </div>

        ${note ? `<div class="task-note">💊 ${escapeHtml(note)}</div>` : ``}
        ${warn ? `<div class="task-note">⚠️ ${escapeHtml(warn)}</div>` : ``}
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

/** Старт */
document.addEventListener("DOMContentLoaded", async () => {
  // грузим историю, затем обновляем UI
  await loadHistory();
  updateCalendar();
});
