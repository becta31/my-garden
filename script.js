/* script.js — FULL (Today cards + Collection + Year) */
/* Требует data.js с массивом plantsData */

function showView(viewName) {
  document.querySelectorAll(".view-section").forEach(v => (v.style.display = "none"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  const view = document.getElementById("view-" + viewName);
  const btn = document.getElementById("btn-" + viewName);
  if (view) view.style.display = "block";
  if (btn) btn.classList.add("active");

  if (viewName === "collection") renderCollection();
  if (viewName === "year") renderYearView();
  if (viewName === "today") updateCalendar();
}

function renderCollection() {
  const list = document.getElementById("collectionList");
  if (!list || !window.plantsData) return;

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
    const lastLog =
      p.history && p.history.length > 0
        ? p.history[p.history.length - 1]
        : { date: "-", event: "Нет записей" };

    const waterText = p.waterFreq === 1 ? "ежедневно" : "раз в " + p.waterFreq + " дн.";

    list.innerHTML += `
      <div class="plant-card">
        <h3>${p.name} <span class="category-tag">${p.category || ""}</span></h3>
        <div class="info-item"><b>📍 Место:</b> ${p.location || "Не указано"}</div>
        <div class="info-item"><b>💧 Полив:</b> ${waterText}</div>
        <div class="history-box"><b>Последнее:</b> ${lastLog.date} — ${lastLog.event}</div>
      </div>
    `;
  });
}

function renderYearView() {
  if (!window.plantsData) return;

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

function updateCalendar() {
  if (!window.plantsData) return;

  const now = new Date();
  const d = now.getDate();
  const m = now.getMonth();

  const months = [
    "Январь","Февраль","Март","Апрель","Май","Июнь",
    "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"
  ];
  const days = ["Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота"];

  const monthName = document.getElementById("monthName");
  const yearNum = document.getElementById("yearNum");
  const dayNum = document.getElementById("dayNum");
  const dayName = document.getElementById("dayName");
  const container = document.getElementById("todayTasks");

  if (monthName) monthName.innerText = months[m];
  if (yearNum) yearNum.innerText = now.getFullYear();
  if (dayNum) dayNum.innerText = d;
  if (dayName) dayName.innerText = days[now.getDay()];
  if (!container) return;

  let html = "";
  let hasTasks = false;

  plantsData.forEach(p => {
    const needWater = p.waterFreq === 1 || (p.waterFreq && d % p.waterFreq === 0);
    if (!needWater) return;

    hasTasks = true;

    const needFeed = Array.isArray(p.feedMonths) && p.feedMonths.includes(m);
    const freqText = p.waterFreq === 1 ? "ежедневно" : `раз в ${p.waterFreq} дн.`;

    const feedText = (p.feedShort || p.feedNote || "").trim();

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

        ${needFeed && feedText ? `<div class="task-note">💊 ${feedText}</div>` : ``}
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

document.addEventListener("DOMContentLoaded", () => {
  updateCalendar();
});
