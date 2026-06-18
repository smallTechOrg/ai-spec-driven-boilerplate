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
                '<div class="stub-banner">⚠ Stub mode — set DATACHAT_GEMINI_API_KEY for live responses</div>'
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
  header { background: #fff; border-bottom: 1px solid #e5e5e5; padding: 14px 24px;
           display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
  header h1 { font-size: 18px; font-weight: 700; }
  #session-label { font-size: 13px; color: #666; }
  #upload-section { flex: 1; display: flex; align-items: center;
                    justify-content: center; }
  #chat-section { flex: 1; display: none; flex-direction: column;
                  overflow: hidden; }
  .drop-zone { border: 2px dashed #cbd5e1; border-radius: 14px;
               padding: 52px 40px; text-align: center; cursor: pointer;
               background: #fff; max-width: 460px; width: 90%;
               transition: border-color .2s, box-shadow .2s; }
  .drop-zone:hover, .drop-zone.drag-over
           { border-color: #6366f1; box-shadow: 0 0 0 4px #e0e7ff; }
  .drop-zone h2 { font-size: 20px; margin-bottom: 8px; }
  .drop-zone p { color: #64748b; font-size: 14px; }
  .btn-upload { display: inline-block; margin-top: 20px; padding: 11px 24px;
                background: #6366f1; color: #fff; border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600; cursor: pointer;
                transition: background .15s; }
  .btn-upload:hover { background: #4f46e5; }
  #upload-hint { font-size: 12px; color: #94a3b8; margin-top: 10px;
                 min-height: 18px; }
  #messages { flex: 1; overflow-y: auto; padding: 24px;
              display: flex; flex-direction: column; gap: 18px; }
  .msg { max-width: 780px; }
  .msg.user { align-self: flex-end; }
  .msg.assistant { align-self: flex-start; width: 100%; }
  .bubble { padding: 13px 17px; border-radius: 14px; font-size: 15px;
            line-height: 1.6; }
  .msg.user .bubble { background: #6366f1; color: #fff;
                      border-radius: 14px 14px 4px 14px; }
  .msg.assistant .bubble { background: #fff; border: 1px solid #e5e5e5;
                            border-radius: 14px 14px 14px 4px; }
  .steps { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
  .step { display: flex; align-items: flex-start; gap: 10px; font-size: 13px;
          color: #475569; padding: 8px 12px; background: #f8fafc;
          border-radius: 8px; border: 1px solid #e2e8f0; }
  .step.error { color: #b91c1c; background: #fef2f2; border-color: #fecaca; }
  .step-icon { flex-shrink: 0; }
  .thinking { display: flex; align-items: center; gap: 8px; font-size: 13px;
              color: #94a3b8; padding: 4px 0; }
  .dots { display: flex; gap: 3px; }
  .dots span { width: 5px; height: 5px; border-radius: 50%; background: #94a3b8;
               animation: pulse 1.2s infinite ease-in-out; }
  .dots span:nth-child(2) { animation-delay: .2s; }
  .dots span:nth-child(3) { animation-delay: .4s; }
  @keyframes pulse { 0%,80%,100%{transform:scale(.7);opacity:.5}
                     40%{transform:scale(1.1);opacity:1} }
  .answer { white-space: pre-wrap; font-size: 15px; }
  .system-msg { font-size: 13px; color: #64748b; padding: 6px 12px;
                background: #f1f5f9; border-radius: 8px; align-self: center; }
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

<!-- Upload screen -->
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

<!-- Chat screen -->
<div id="chat-section">
  <div id="messages"></div>
  <div id="input-row">
    <textarea id="q" placeholder="Ask a question about your data…" rows="1"></textarea>
    <button id="send" onclick="sendQuestion()">Send</button>
  </div>
</div>

<script>
let sessionId = null;

// ── Upload ────────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadHint = document.getElementById('upload-hint');

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', e => handleFile(e.target.files[0]));

async function handleFile(file) {
  if (!file) return;
  uploadHint.textContent = 'Uploading…';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/api/sessions', { method: 'POST', body: fd });
    const body = await r.json();
    if (!r.ok) {
      uploadHint.textContent = body.detail?.message || 'Upload failed — try again';
      return;
    }
    const data = body.data;
    sessionId = data.session_id;
    document.getElementById('session-label').textContent =
      data.filename + '  ·  ' + data.row_count.toLocaleString() + ' rows';
    document.getElementById('upload-section').style.display = 'none';
    const chat = document.getElementById('chat-section');
    chat.style.display = 'flex';
    addSystemMsg(
      'Loaded ' + data.column_names.length + ' columns: ' +
      data.column_names.join(', ') + '. Ask me anything about your data.'
    );
    document.getElementById('q').focus();
  } catch (e) {
    uploadHint.textContent = 'Error: ' + e.message;
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────
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

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendQuestion() {
  const input = document.getElementById('q');
  const send  = document.getElementById('send');
  const question = input.value.trim();
  if (!question || !sessionId) return;

  input.value = '';
  send.disabled = true;

  // User bubble
  const userEl = document.createElement('div');
  userEl.className = 'msg user';
  userEl.innerHTML = '<div class="bubble">' + esc(question) + '</div>';
  messagesEl.appendChild(userEl);

  // Assistant bubble — built as events arrive
  const assistEl = document.createElement('div');
  assistEl.className = 'msg assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const stepsEl = document.createElement('div');
  stepsEl.className = 'steps';
  bubble.appendChild(stepsEl);
  assistEl.appendChild(bubble);
  messagesEl.appendChild(assistEl);

  // Thinking indicator while we wait for the first event
  addThinking(stepsEl);
  scrollBottom();

  try {
    const resp = await fetch('/api/sessions/' + sessionId + '/messages/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      removeThinking(stepsEl);
      addAnswer(bubble, (err.detail?.message || 'Something went wrong — please try again'), true);
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
      buf = lines.pop();          // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') break;
        let event;
        try { event = JSON.parse(raw); } catch { continue; }
        handleEvent(event, stepsEl, bubble);
        scrollBottom();
      }
    }
  } catch (e) {
    removeThinking(stepsEl);
    addAnswer(bubble, 'Network error — please try again', true);
  } finally {
    send.disabled = false;
    input.focus();
  }
}

function handleEvent(event, stepsEl, bubble) {
  if (event.type === 'thinking') {
    // Show the indicator only if it isn't already there
    if (!stepsEl.querySelector('.thinking')) addThinking(stepsEl);
    return;
  }

  if (event.type === 'step') {
    removeThinking(stepsEl);
    const el = document.createElement('div');
    el.className = 'step' + (event.is_error ? ' error' : '');
    el.innerHTML =
      '<span class="step-icon">' + (event.is_error ? '⚠' : '✓') + '</span>' +
      '<span>' + esc(event.description) + '</span>';
    stepsEl.appendChild(el);
    // Add thinking indicator for the next step
    addThinking(stepsEl);
    return;
  }

  if (event.type === 'answer') {
    removeThinking(stepsEl);
    // Remove the steps container if no steps ran (e.g. 1-shot FINAL ANSWER)
    if (!stepsEl.children.length) stepsEl.remove();
    addAnswer(bubble, event.answer, false);
    return;
  }

  if (event.type === 'error') {
    removeThinking(stepsEl);
    addAnswer(bubble, event.message, true);
  }
}

function addThinking(stepsEl) {
  const el = document.createElement('div');
  el.className = 'thinking';
  el.innerHTML = '<span>Thinking</span><div class="dots">' +
    '<span></span><span></span><span></span></div>';
  stepsEl.appendChild(el);
}

function removeThinking(stepsEl) {
  const el = stepsEl.querySelector('.thinking');
  if (el) el.remove();
}

function addAnswer(bubble, text, isError) {
  const el = document.createElement('div');
  el.className = 'answer';
  if (isError) el.style.color = '#b91c1c';
  el.textContent = text;
  bubble.appendChild(el);
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
</script>
</body>
</html>
"""
