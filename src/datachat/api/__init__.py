import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from datachat.db.session import init_db
    from datachat.llm.client import get_llm_client
    init_db()
    get_llm_client()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="DataChat", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from datachat.api import health, sessions, chat, stream
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)
    app.include_router(stream.router)

    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    if os.path.isdir(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def index():
            from datachat.config.settings import get_settings
            provider = get_settings().resolved_llm_provider
            stub_banner = (
                '<div class="stub-banner">&#9888; Stub mode — set DATACHAT_GEMINI_API_KEY for live responses</div>'
                if provider == "stub" else ""
            )
            return _CHAT_HTML.replace("{{STUB_BANNER}}", stub_banner)

    return app


app = create_app()


_CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DataChat</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f0f2f5; color: #1a1a1a; height: 100vh;
         display: flex; flex-direction: column; }

  .stub-banner { background: #fbbf24; padding: 10px; text-align: center;
                 font-weight: 600; font-size: 13px; flex-shrink: 0; }

  header { background: #fff; border-bottom: 1px solid #e5e5e5;
           padding: 14px 24px; display: flex; align-items: center;
           gap: 12px; flex-shrink: 0; }
  header h1 { font-size: 18px; font-weight: 700; }
  #session-label { font-size: 13px; color: #666; }

  /* ── Upload screen ─────────────────────────────── */
  #upload-section { flex: 1; display: flex; align-items: center;
                    justify-content: center; }
  .drop-zone { border: 2px dashed #cbd5e1; border-radius: 14px;
               padding: 52px 40px; text-align: center; cursor: pointer;
               background: #fff; max-width: 460px; width: 90%;
               transition: border-color .2s, box-shadow .2s; }
  .drop-zone:hover, .drop-zone.drag-over
    { border-color: #6366f1; box-shadow: 0 0 0 4px #e0e7ff; }
  .drop-zone h2 { font-size: 20px; margin-bottom: 8px; }
  .drop-zone p  { color: #64748b; font-size: 14px; }
  .btn-upload { display: inline-block; margin-top: 20px; padding: 11px 24px;
                background: #6366f1; color: #fff; border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600; cursor: pointer;
                transition: background .15s; }
  .btn-upload:hover { background: #4f46e5; }
  #upload-hint { font-size: 12px; color: #94a3b8; margin-top: 10px;
                 min-height: 18px; }

  /* ── Chat screen ───────────────────────────────── */
  #chat-section { flex: 1; display: none; flex-direction: column; overflow: hidden; }
  #messages { flex: 1; overflow-y: auto; padding: 24px;
              display: flex; flex-direction: column; gap: 18px; }

  .msg { max-width: 760px; }
  .msg.user      { align-self: flex-end; }
  .msg.assistant { align-self: flex-start; width: 100%; }

  .bubble { padding: 13px 17px; border-radius: 14px; font-size: 15px; line-height: 1.6; }
  .msg.user .bubble { background: #6366f1; color: #fff;
                      border-radius: 14px 14px 4px 14px; }
  .msg.assistant .bubble { background: #fff; border: 1px solid #e5e5e5;
                            border-radius: 14px 14px 14px 4px; }

  /* progress area inside assistant bubble */
  .progress-area { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }

  /* individual completed step — only shows description, no raw data */
  .step { display: flex; align-items: center; gap: 9px; font-size: 13px;
          color: #475569; padding: 7px 12px; background: #f8fafc;
          border-radius: 8px; border: 1px solid #e2e8f0;
          animation: slide-in .25s ease; }
  .step.error { color: #b91c1c; background: #fef2f2; border-color: #fecaca; }
  @keyframes slide-in { from { opacity:0; transform:translateY(-4px) }
                        to   { opacity:1; transform:translateY(0)     } }

  /* live status row — shows while agent is working */
  .status-row { display: flex; align-items: center; gap: 10px;
                font-size: 13px; color: #6366f1; padding: 4px 0; }
  .status-text { font-weight: 500; }
  .timer { font-size: 12px; color: #94a3b8; margin-left: 4px; }
  .dots { display: flex; gap: 3px; }
  .dots span { width: 5px; height: 5px; border-radius: 50%; background: #6366f1;
               animation: pulse 1.2s infinite ease-in-out; }
  .dots span:nth-child(2) { animation-delay: .2s; }
  .dots span:nth-child(3) { animation-delay: .4s; }
  @keyframes pulse { 0%,80%,100%{transform:scale(.7);opacity:.5}
                     40%{transform:scale(1.1);opacity:1} }

  /* final answer text */
  .answer { white-space: pre-wrap; font-size: 15px; }
  .answer.error { color: #b91c1c; }

  .system-msg { font-size: 13px; color: #64748b; padding: 6px 12px;
                background: #f1f5f9; border-radius: 8px; align-self: center; }

  /* ── Input row ─────────────────────────────────── */
  #input-row { padding: 14px 20px; background: #fff;
               border-top: 1px solid #e5e5e5; display: flex;
               gap: 10px; align-items: flex-end; flex-shrink: 0; }
  #q { flex: 1; padding: 11px 14px; border: 1px solid #e5e5e5;
       border-radius: 10px; font-size: 15px; font-family: inherit;
       resize: none; outline: none; min-height: 46px; max-height: 140px;
       overflow-y: auto; transition: border-color .2s; }
  #q:focus { border-color: #6366f1; }
  #send { padding: 11px 22px; background: #6366f1; color: #fff; border: none;
          border-radius: 10px; font-size: 15px; font-weight: 600;
          cursor: pointer; transition: background .15s; }
  #send:hover:not(:disabled) { background: #4f46e5; }
  #send:disabled { opacity: .45; cursor: not-allowed; }
</style>
</head>
<body>
{{STUB_BANNER}}

<header>
  <h1>DataChat</h1>
  <span id="session-label"></span>
</header>

<div id="upload-section">
  <div class="drop-zone" id="drop-zone">
    <h2>Upload your data</h2>
    <p>Drop a CSV or JSON file here, or click to browse</p>
    <input type="file" id="file-input" accept=".csv,.json" style="display:none">
    <button class="btn-upload" onclick="document.getElementById('file-input').click()">
      Choose file
    </button>
    <p id="upload-hint"></p>
  </div>
</div>

<div id="chat-section">
  <div id="messages"></div>
  <div id="input-row">
    <textarea id="q" placeholder="Ask a question about your data&#8230;" rows="1"></textarea>
    <button id="send" onclick="sendQuestion()">Send</button>
  </div>
</div>

<script>
let sessionId = null;

// ── Upload ──────────────────────────────────────────────────────────────────
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const uploadHint = document.getElementById('upload-hint');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', e => handleFile(e.target.files[0]));

async function handleFile(file) {
  if (!file) return;
  uploadHint.textContent = 'Uploading…';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r    = await fetch('/api/sessions', { method: 'POST', body: fd });
    const body = await r.json();
    if (!r.ok) { uploadHint.textContent = body.detail?.message || 'Upload failed — try again'; return; }
    const data = body.data;
    sessionId  = data.session_id;
    document.getElementById('session-label').textContent =
      data.filename + '  ·  ' + data.row_count.toLocaleString() + ' rows';
    document.getElementById('upload-section').style.display = 'none';
    const chat = document.getElementById('chat-section');
    chat.style.display = 'flex';
    addSystemMsg('Loaded ' + data.column_names.length + ' columns: ' +
      data.column_names.join(', ') + '. Ask me anything about your data.');
    document.getElementById('q').focus();
  } catch (e) { uploadHint.textContent = 'Error: ' + e.message; }
}

// ── Chat ────────────────────────────────────────────────────────────────────
const messagesEl = document.getElementById('messages');

document.getElementById('q').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
});

function addSystemMsg(text) {
  const el = document.createElement('div');
  el.className = 'system-msg';
  el.textContent = text;
  messagesEl.appendChild(el);
  scrollBottom();
}

function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

// pause one animation frame so the browser can repaint before the next event
function nextFrame() { return new Promise(r => requestAnimationFrame(r)); }

async function sendQuestion() {
  const input = document.getElementById('q');
  const send  = document.getElementById('send');
  const question = input.value.trim();
  if (!question || !sessionId) return;

  input.value  = '';
  send.disabled = true;

  // User bubble
  const userEl = document.createElement('div');
  userEl.className = 'msg user';
  userEl.innerHTML = '<div class="bubble">' + esc(question) + '</div>';
  messagesEl.appendChild(userEl);
  scrollBottom();

  // Assistant bubble — built incrementally
  const assistEl = document.createElement('div');
  assistEl.className = 'msg assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const progressArea = document.createElement('div');
  progressArea.className = 'progress-area';
  bubble.appendChild(progressArea);
  assistEl.appendChild(bubble);
  messagesEl.appendChild(assistEl);

  // Live status row with elapsed timer
  const statusRow = createStatusRow('Working out how to answer your question');
  progressArea.appendChild(statusRow);
  const startTime = Date.now();
  const timerInterval = setInterval(() => {
    const s = Math.floor((Date.now() - startTime) / 1000);
    statusRow.querySelector('.timer').textContent = s + 's';
  }, 500);
  scrollBottom();

  try {
    const resp = await fetch('/api/sessions/' + sessionId + '/messages/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!resp.ok) {
      clearInterval(timerInterval);
      const err = await resp.json().catch(() => ({}));
      statusRow.remove();
      addAnswer(bubble, err.detail?.message || 'Something went wrong — please try again', true);
      return;
    }

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\\n');
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') break;
        let event;
        try { event = JSON.parse(raw); } catch { continue; }
        // Yield to the browser so each event visually appears before the next
        await nextFrame();
        handleEvent(event, progressArea, bubble, statusRow, startTime);
        scrollBottom();
      }
    }
  } catch (e) {
    addAnswer(bubble, 'Connection lost — please try again', true);
  } finally {
    clearInterval(timerInterval);
    statusRow.remove();
    send.disabled = false;
    input.focus();
  }
}

function handleEvent(event, progressArea, bubble, statusRow, startTime) {
  if (event.type === 'thinking') {
    // Update the status text to reflect we are now running a calculation
    const txt = progressArea.querySelector('.status-text');
    if (txt) txt.textContent = 'Running a calculation';
    return;
  }

  if (event.type === 'step') {
    // Add completed step (description only — no raw data)
    const el = document.createElement('div');
    el.className = 'step' + (event.is_error ? ' error' : '');
    el.innerHTML =
      '<span>' + (event.is_error ? '⚠' : '✓') + '</span>' +
      '<span>' + esc(event.description) + '</span>';
    // Insert before the status row so it appears above the spinner
    progressArea.insertBefore(el, statusRow);
    // Update status to preparing next step
    const txt = progressArea.querySelector('.status-text');
    if (txt) txt.textContent = 'Checking what else is needed';
    return;
  }

  if (event.type === 'answer') {
    const elapsed = Math.round((Date.now() - startTime) / 1000);
    addAnswer(bubble, event.answer, false);
    // Add subtle time footer
    const footer = document.createElement('div');
    footer.style.cssText = 'font-size:11px;color:#94a3b8;margin-top:6px;';
    footer.textContent = 'Answered in ' + elapsed + 's';
    bubble.appendChild(footer);
    return;
  }

  if (event.type === 'error') {
    addAnswer(bubble, event.message, true);
  }
}

function createStatusRow(text) {
  const el = document.createElement('div');
  el.className = 'status-row';
  el.innerHTML =
    '<div class="dots"><span></span><span></span><span></span></div>' +
    '<span class="status-text">' + esc(text) + '</span>' +
    '<span class="timer">0s</span>';
  return el;
}

function addAnswer(bubble, text, isError) {
  const el = document.createElement('div');
  el.className = 'answer' + (isError ? ' error' : '');
  el.textContent = text;
  bubble.appendChild(el);
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
</script>
</body>
</html>
"""
