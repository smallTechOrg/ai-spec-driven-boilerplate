// localStorage keys
const LS_OFFICER = 'uppolice_officer';
const LS_ASSESSMENT = 'uppolice_assessment';
const LS_PLAN = 'uppolice_plan';

const AREA_SEQUENCE = ['A', 'B', 'C', 'D'];
const AREA_ICONS = { A: '🤖', B: '🔐', C: '📡', D: '📷' };
const AREA_NAMES = { A: 'AI Tools', B: 'Cybersecurity', C: 'Comms & Data', D: 'CCTV & Surveillance' };
const LEVEL_NAMES = { B: 'Beginner', I: 'Intermediate', V: 'Advanced' };

// ─── Storage helpers ──────────────────────────────────────────────────────────

function getOfficer() {
  try { return JSON.parse(localStorage.getItem(LS_OFFICER)); } catch { return null; }
}

function getAssessment() {
  try { return JSON.parse(localStorage.getItem(LS_ASSESSMENT)); } catch { return null; }
}

function getPlan() {
  try { return JSON.parse(localStorage.getItem(LS_PLAN)); } catch { return null; }
}

function saveOfficer(data) { localStorage.setItem(LS_OFFICER, JSON.stringify(data)); }
function saveAssessment(data) { localStorage.setItem(LS_ASSESSMENT, JSON.stringify(data)); }
function savePlan(data) { localStorage.setItem(LS_PLAN, JSON.stringify(data)); }

// ─── Plan generation ──────────────────────────────────────────────────────────

function getLevelCode(avg) {
  if (avg < 2.5) return 'B';
  if (avg < 3.75) return 'I';
  return 'V';
}

function avg(scores) {
  const vals = scores.filter(v => v != null && !isNaN(v));
  if (!vals.length) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function computeAverages(scores) {
  return {
    A: avg([scores.a1, scores.a2, scores.a3, scores.a4, scores.a5]),
    B: avg([scores.b1, scores.b2, scores.b3, scores.b4, scores.b5]),
    C: avg([scores.c1, scores.c2, scores.c3, scores.c4, scores.c5]),
    D: avg([scores.d1, scores.d2, scores.d3, scores.d4, scores.d5]),
  };
}

function generatePlan(averages) {
  const levelCodes = {
    A: getLevelCode(averages.A),
    B: getLevelCode(averages.B),
    C: getLevelCode(averages.C),
    D: getLevelCode(averages.D),
  };
  const days = [];
  for (let dayNum = 1; dayNum <= 30; dayNum++) {
    const area = AREA_SEQUENCE[(dayNum - 1) % 4];
    const occurrence = Math.floor((dayNum - 1) / 4);
    const taskIdx = occurrence % 5;
    const levelCode = levelCodes[area];
    const taskKey = `${area}_${levelCode}_${taskIdx}`;
    days.push({
      dayNumber: dayNum,
      area,
      levelCode,
      taskKey,
      status: 'not_started',
      completedAt: null,
    });
  }
  return days;
}

// ─── Header renderer ──────────────────────────────────────────────────────────

function renderHeader(currentPage) {
  const officer = getOfficer();
  const nav = document.getElementById('header-nav');
  if (!nav) return;
  if (officer) {
    nav.innerHTML = `
      <span>${officer.name}</span>
      <a href="/" onclick="logout(event)">Log out</a>
    `;
  }
}

function logout(e) {
  e.preventDefault();
  localStorage.removeItem(LS_OFFICER);
  localStorage.removeItem(LS_ASSESSMENT);
  localStorage.removeItem(LS_PLAN);
  window.location.href = '/';
}

// ─── Page: index ─────────────────────────────────────────────────────────────

function initIndex() {
  renderHeader();
  const officer = getOfficer();
  const assessment = getAssessment();
  const plan = getPlan();

  const welcome = document.getElementById('welcome-section');
  const register = document.getElementById('register-section');

  if (officer) {
    register.style.display = 'none';
    welcome.style.display = 'block';
    document.getElementById('welcome-name').textContent = officer.name;

    const done = plan ? plan.filter(d => d.status === 'done').length : 0;
    document.getElementById('welcome-progress').textContent =
      plan ? `${done}/30 days completed` : 'Assessment not yet completed';

    document.getElementById('btn-continue').href = assessment ? 'plan.html' : 'assessment.html';
    document.getElementById('btn-continue').textContent = assessment ? 'View My 30-Day Plan →' : 'Take Assessment →';
  } else {
    welcome.style.display = 'none';
    register.style.display = 'block';
  }

  const form = document.getElementById('register-form');
  if (form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const name = document.getElementById('reg-name').value.trim();
      const badge = document.getElementById('reg-badge').value.trim().toUpperCase();
      if (!name || !badge) return;
      saveOfficer({ name, badgeNumber: badge, registeredAt: new Date().toISOString() });
      window.location.href = 'assessment.html';
    });
  }

  const retakeBtn = document.getElementById('btn-retake');
  if (retakeBtn) {
    retakeBtn.addEventListener('click', function() {
      localStorage.removeItem(LS_ASSESSMENT);
      localStorage.removeItem(LS_PLAN);
      window.location.href = 'assessment.html';
    });
  }
}

// ─── Page: assessment ────────────────────────────────────────────────────────

async function initAssessment() {
  renderHeader();
  const officer = getOfficer();
  if (!officer) { window.location.href = '/'; return; }

  let appData;
  try {
    const res = await fetch('data/data.json');
    appData = await res.json();
  } catch {
    document.getElementById('assessment-container').innerHTML =
      '<p class="alert alert-info">Could not load assessment data. Make sure you are running via a local server.</p>';
    return;
  }

  document.getElementById('officer-name-display').textContent = officer.name;

  const container = document.getElementById('assessment-container');
  const sections = appData.sections;

  sections.forEach((section, sIdx) => {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'card';
    sectionDiv.innerHTML = `
      <div class="section-header">
        <span class="icon">${section.icon}</span>
        <h3>Section ${section.id} — ${section.name}</h3>
      </div>
      <div class="rating-scale-labels">
        <span>1 = No experience</span>
        <span>3 = Some experience</span>
        <span>5 = Confident / Expert</span>
      </div>
    `;
    section.questions.forEach((q) => {
      const row = document.createElement('div');
      row.className = 'rating-row';
      row.innerHTML = `
        <span class="rating-question">${q.text}</span>
        <div class="rating-options">
          ${[1,2,3,4,5].map(v => `
            <label>
              <input type="radio" name="${q.id}" value="${v}" required>
              <span class="score-btn">${v}</span>
            </label>
          `).join('')}
        </div>
      `;
      sectionDiv.appendChild(row);
    });
    container.appendChild(sectionDiv);
  });

  document.getElementById('assessment-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const fd = new FormData(this);
    const scores = {};
    for (const [k, v] of fd.entries()) scores[k] = parseFloat(v);

    // Validate all 20 answered
    const allIds = sections.flatMap(s => s.questions.map(q => q.id));
    if (allIds.some(id => !scores[id])) {
      alert('Please rate all questions before submitting.');
      return;
    }

    const averages = computeAverages(scores);
    const overallAvg = avg(Object.values(averages));
    const assessment = { scores, averages, overallAvg, completedAt: new Date().toISOString() };
    saveAssessment(assessment);

    const plan = generatePlan(averages);
    savePlan(plan);

    window.location.href = 'plan.html';
  });
}

// ─── Page: plan ──────────────────────────────────────────────────────────────

async function initPlan() {
  renderHeader();
  const officer = getOfficer();
  const assessment = getAssessment();
  let plan = getPlan();

  if (!officer) { window.location.href = '/'; return; }
  if (!assessment || !plan) { window.location.href = 'assessment.html'; return; }

  let appData;
  try {
    const res = await fetch('data/data.json');
    appData = await res.json();
  } catch {
    document.getElementById('plan-container').innerHTML =
      '<p class="alert alert-info">Could not load task data. Make sure you are running via a local server.</p>';
    return;
  }

  const tasks = appData.tasks;

  // Officer info
  document.getElementById('plan-officer-name').textContent = officer.name;
  document.getElementById('plan-badge').textContent = officer.badgeNumber;

  // Progress
  const done = plan.filter(d => d.status === 'done').length;
  const inProgress = plan.filter(d => d.status === 'in_progress').length;
  document.getElementById('progress-done').textContent = done;
  document.getElementById('progress-total').textContent = 30;
  document.getElementById('progress-bar').style.width = `${Math.round((done / 30) * 100)}%`;
  document.getElementById('progress-label').textContent =
    `${done} done · ${inProgress} in progress · ${30 - done - inProgress} not started`;

  // Score badges
  const badgesEl = document.getElementById('score-badges');
  const sections = appData.sections;
  sections.forEach(s => {
    const avg = assessment.averages[s.id];
    const levelCode = getLevelCode(avg);
    const levelName = LEVEL_NAMES[levelCode];
    const levelClass = levelName.toLowerCase();
    badgesEl.innerHTML += `
      <span class="score-badge ${levelClass}">
        ${s.icon} ${s.name}: ${levelName} (${avg.toFixed(1)})
      </span>
    `;
  });

  // Today's task (first non-done)
  const todayDay = plan.find(d => d.status !== 'done') || plan[plan.length - 1];
  const todayTask = tasks[todayDay.taskKey];
  if (todayTask) {
    document.getElementById('today-day').textContent = `Day ${todayDay.dayNumber}`;
    document.getElementById('today-area').textContent =
      `${AREA_ICONS[todayDay.area]} ${AREA_NAMES[todayDay.area]}`;
    document.getElementById('today-level').textContent = LEVEL_NAMES[todayDay.levelCode];
    document.getElementById('today-task').textContent = todayTask.task;
    document.getElementById('today-resource').textContent = todayTask.resource;
    document.getElementById('today-time').textContent = `${todayTask.minutes} min`;

    const markBtn = document.getElementById('today-mark-done');
    if (todayDay.status !== 'done') {
      markBtn.addEventListener('click', () => updateDayStatus(todayDay.dayNumber, 'done', plan));
    } else {
      markBtn.textContent = '✅ Done';
      markBtn.disabled = true;
      markBtn.classList.add('btn-outline');
    }
  }

  // Full 30-day table
  const tbody = document.getElementById('plan-tbody');
  plan.forEach(day => {
    const task = tasks[day.taskKey] || {};
    const statusIcon = { done: '✅', in_progress: '⏳', not_started: '⬜' }[day.status];
    const statusClass = { done: 'status-done', in_progress: 'status-in_progress', not_started: '' }[day.status];
    const areaClass = `area-${day.area}`;
    const levelClass = `level-${LEVEL_NAMES[day.levelCode] || 'Beginner'}`;

    const tr = document.createElement('tr');
    tr.className = statusClass;
    tr.dataset.day = day.dayNumber;
    tr.innerHTML = `
      <td><span class="day-num">${day.dayNumber}</span></td>
      <td><span class="area-pill ${areaClass}">${AREA_ICONS[day.area]} ${AREA_NAMES[day.area]}</span></td>
      <td><span class="level-pill ${levelClass}">${LEVEL_NAMES[day.levelCode]}</span></td>
      <td>
        <div class="task-text">${task.task || '—'}</div>
        <div class="resource-link">${task.resource || ''}</div>
      </td>
      <td class="time-chip">${task.minutes ? task.minutes + ' min' : '—'}</td>
      <td>
        <select class="status-select" data-day="${day.dayNumber}">
          <option value="not_started" ${day.status === 'not_started' ? 'selected' : ''}>⬜ Not Started</option>
          <option value="in_progress" ${day.status === 'in_progress' ? 'selected' : ''}>⏳ In Progress</option>
          <option value="done" ${day.status === 'done' ? 'selected' : ''}>✅ Done</option>
        </select>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Status change listeners
  tbody.addEventListener('change', function(e) {
    if (e.target.classList.contains('status-select')) {
      const dayNum = parseInt(e.target.dataset.day);
      const newStatus = e.target.value;
      updateDayStatus(dayNum, newStatus, plan, false);
    }
  });
}

function updateDayStatus(dayNumber, newStatus, plan, reload = true) {
  plan = plan || getPlan();
  const day = plan.find(d => d.dayNumber === dayNumber);
  if (!day) return;
  day.status = newStatus;
  day.completedAt = newStatus === 'done' ? new Date().toISOString() : null;
  savePlan(plan);
  if (reload) {
    window.location.reload();
  } else {
    // Update progress bar in place
    const done = plan.filter(d => d.status === 'done').length;
    const inProgress = plan.filter(d => d.status === 'in_progress').length;
    const bar = document.getElementById('progress-bar');
    if (bar) bar.style.width = `${Math.round((done / 30) * 100)}%`;
    const label = document.getElementById('progress-label');
    if (label) label.textContent = `${done} done · ${inProgress} in progress · ${30 - done - inProgress} not started`;
    const doneEl = document.getElementById('progress-done');
    if (doneEl) doneEl.textContent = done;

    // Update row styling
    const tr = document.querySelector(`tr[data-day="${dayNumber}"]`);
    if (tr) {
      tr.className = { done: 'status-done', in_progress: 'status-in_progress', not_started: '' }[newStatus];
    }
  }
}
