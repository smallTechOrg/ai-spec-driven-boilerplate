// File handles — kept in memory for the session
let jsonHandle = null;
let jsHandle = null;
let currentData = null;

const AREA_IDS = ['A', 'B', 'C', 'D'];
const AREA_NAMES = { A: 'AI Tools & General Literacy', B: 'Cybersecurity & AI Threats', C: 'Communication & Data Analytics', D: 'CCTV & Surveillance AI' };
const AREA_ICONS = { A: '🤖', B: '🔐', C: '📡', D: '📷' };
const LEVELS = [
  { code: 'B', name: 'Beginner' },
  { code: 'I', name: 'Intermediate' },
  { code: 'V', name: 'Advanced' },
];

// ─── File access ─────────────────────────────────────────────────────────────

async function openJsonFile() {
  try {
    [jsonHandle] = await window.showOpenFilePicker({
      id: 'dataJson',
      types: [{ description: 'JSON file', accept: { 'application/json': ['.json'] } }],
    });
    const file = await jsonHandle.getFile();
    currentData = JSON.parse(await file.text());
    updateFileStatus('json-status', jsonHandle.name, true);
    checkBothFilesReady();
  } catch (e) {
    if (e.name !== 'AbortError') showError('Could not open data.json: ' + e.message);
  }
}

async function openJsFile() {
  try {
    [jsHandle] = await window.showOpenFilePicker({
      id: 'dataJs',
      types: [{ description: 'JavaScript file', accept: { 'text/javascript': ['.js'] } }],
    });
    updateFileStatus('js-status', jsHandle.name, true);
    checkBothFilesReady();
  } catch (e) {
    if (e.name !== 'AbortError') showError('Could not open data.js: ' + e.message);
  }
}

function checkBothFilesReady() {
  if (jsonHandle && jsHandle) {
    document.getElementById('setup-section').classList.add('setup-done');
    document.getElementById('editor-section').style.display = 'block';
    document.getElementById('save-bar').style.display = 'flex';
    buildEditor();
  }
}

async function saveFiles() {
  if (!jsonHandle || !jsHandle || !currentData) return;
  collectFormData();

  const jsonContent = JSON.stringify(currentData, null, 2);
  const jsContent = `const APP_DATA = ${jsonContent};\n`;

  try {
    const w1 = await jsonHandle.createWritable();
    await w1.write(jsonContent);
    await w1.close();

    const w2 = await jsHandle.createWritable();
    await w2.write(jsContent);
    await w2.close();

    showSaveConfirmation();
  } catch (e) {
    showError('Save failed: ' + e.message);
  }
}

// ─── Build the editor ────────────────────────────────────────────────────────

function buildEditor() {
  buildQuestionsEditor();
  buildTasksEditor();

  // Default tab
  switchTab('questions');

  // Area/level selectors for tasks
  selectArea('A');
  selectLevel('B');
}

// Questions editor
function buildQuestionsEditor() {
  const container = document.getElementById('questions-editor');
  container.innerHTML = '';

  currentData.sections.forEach(section => {
    const card = document.createElement('div');
    card.className = 'card admin-section-card';
    card.innerHTML = `
      <div class="section-header">
        <span class="icon">${section.icon}</span>
        <h3>Section ${section.id} — ${section.name}</h3>
      </div>
    `;
    section.questions.forEach((q, idx) => {
      const row = document.createElement('div');
      row.className = 'admin-field-row';
      row.innerHTML = `
        <label class="admin-field-label">Q${idx + 1}</label>
        <input type="text" class="admin-input" data-section="${section.id}" data-qidx="${idx}"
               value="${escapeAttr(q.text)}" placeholder="Question text">
      `;
      card.appendChild(row);
    });
    container.appendChild(card);
  });
}

// Tasks editor
function buildTasksEditor() {
  const areaNav = document.getElementById('area-nav');
  areaNav.innerHTML = '';
  AREA_IDS.forEach(id => {
    const btn = document.createElement('button');
    btn.className = 'tab-btn';
    btn.dataset.area = id;
    btn.textContent = `${AREA_ICONS[id]} ${AREA_NAMES[id].split(' ')[0]}`;
    btn.onclick = () => selectArea(id);
    areaNav.appendChild(btn);
  });

  const levelNav = document.getElementById('level-nav');
  levelNav.innerHTML = '';
  LEVELS.forEach(l => {
    const btn = document.createElement('button');
    btn.className = 'tab-btn';
    btn.dataset.level = l.code;
    btn.textContent = l.name;
    btn.onclick = () => selectLevel(l.code);
    levelNav.appendChild(btn);
  });
}

let activeArea = 'A';
let activeLevel = 'B';

function selectArea(areaId) {
  activeArea = areaId;
  document.querySelectorAll('#area-nav .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.area === areaId));
  renderTaskCards();
}

function selectLevel(levelCode) {
  activeLevel = levelCode;
  document.querySelectorAll('#level-nav .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.level === levelCode));
  renderTaskCards();
}

function renderTaskCards() {
  const container = document.getElementById('tasks-editor');
  container.innerHTML = '';

  const levelName = LEVELS.find(l => l.code === activeLevel).name;
  const areaName = AREA_NAMES[activeArea];

  const header = document.createElement('div');
  header.className = 'admin-tasks-header';
  header.innerHTML = `<span>${AREA_ICONS[activeArea]} ${areaName}</span><span class="level-pill level-${levelName}">${levelName}</span>`;
  container.appendChild(header);

  for (let i = 0; i < 5; i++) {
    const key = `${activeArea}_${activeLevel}_${i}`;
    const task = currentData.tasks[key] || { task: '', resource: '', minutes: 30 };

    const card = document.createElement('div');
    card.className = 'card admin-task-card';
    card.innerHTML = `
      <div class="admin-task-num">Task ${i + 1} <code class="task-key">${key}</code></div>
      <div class="admin-field-row">
        <label class="admin-field-label">Description</label>
        <input type="text" class="admin-input" data-key="${key}" data-field="task"
               value="${escapeAttr(task.task)}" placeholder="What the officer should do today">
      </div>
      <div class="admin-field-row">
        <label class="admin-field-label">Resource</label>
        <input type="text" class="admin-input" data-key="${key}" data-field="resource"
               value="${escapeAttr(task.resource)}" placeholder="Tool, link, or reference">
      </div>
      <div class="admin-field-row admin-field-row-short">
        <label class="admin-field-label">Time (min)</label>
        <input type="number" class="admin-input admin-input-short" data-key="${key}" data-field="minutes"
               value="${task.minutes}" min="5" max="120" step="5">
      </div>
    `;
    container.appendChild(card);
  }
}

// ─── Collect form data back into currentData ─────────────────────────────────

function collectFormData() {
  // Questions
  document.querySelectorAll('[data-section][data-qidx]').forEach(input => {
    const sectionId = input.dataset.section;
    const qIdx = parseInt(input.dataset.qidx);
    const section = currentData.sections.find(s => s.id === sectionId);
    if (section) section.questions[qIdx].text = input.value.trim();
  });

  // Tasks
  document.querySelectorAll('[data-key][data-field]').forEach(input => {
    const key = input.dataset.key;
    const field = input.dataset.field;
    if (!currentData.tasks[key]) currentData.tasks[key] = { task: '', resource: '', minutes: 30 };
    currentData.tasks[key][field] = field === 'minutes' ? parseInt(input.value) : input.value.trim();
  });
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

function switchTab(tab) {
  document.querySelectorAll('.main-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('tab-questions').style.display = tab === 'questions' ? 'block' : 'none';
  document.getElementById('tab-tasks').style.display = tab === 'tasks' ? 'block' : 'none';
}

// ─── UI helpers ──────────────────────────────────────────────────────────────

function updateFileStatus(id, name, ok) {
  const el = document.getElementById(id);
  el.textContent = ok ? `✅ ${name}` : '—';
  el.className = ok ? 'file-status ok' : 'file-status';
}

function showError(msg) {
  const el = document.getElementById('error-bar');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 5000);
}

function showSaveConfirmation() {
  const el = document.getElementById('save-confirm');
  el.style.display = 'inline-block';
  el.style.opacity = '1';
  setTimeout(() => {
    el.style.transition = 'opacity 0.6s';
    el.style.opacity = '0';
    setTimeout(() => { el.style.display = 'none'; el.style.transition = ''; }, 700);
  }, 2500);
}

function escapeAttr(str) {
  return (str || '').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
