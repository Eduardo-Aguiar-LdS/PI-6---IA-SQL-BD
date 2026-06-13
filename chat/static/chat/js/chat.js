const SESSION_ID   = window.SESSION_ID;
const CSRF_TOKEN   = window.CSRF_TOKEN;
const messagesArea = document.getElementById('messages-area');
const promptInput  = document.getElementById('prompt-input');

/* ── TEXTAREA ── */
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function scrollBottom() { if (messagesArea) messagesArea.scrollTop = messagesArea.scrollHeight; }
function nowTime() {
  const d = new Date();
  return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}

/* ── MESSAGES ── */
function appendMessage(role, content, time) {
  const isUser = role === 'user';
  const group = document.createElement('div');
  group.className = 'message-group';
  group.innerHTML = `
    <div class="message ${role}">
      <div class="msg-avatar ${role}">${isUser ? window.USER_INITIALS : 'O'}</div>
      <div class="msg-content">
        <span class="msg-sender">${isUser ? window.USER_NAME : 'Omni Mind'}</span>
        <div class="msg-bubble">${content}</div>
        <span class="msg-time">${time || nowTime()}</span>
      </div>
    </div>`;
  messagesArea.appendChild(group);
  scrollBottom();
}

function showTyping() {
  const g = document.createElement('div');
  g.className = 'message-group'; g.id = 'typing-group';
  g.innerHTML = `<div class="message ai"><div class="msg-avatar ai">O</div><div class="msg-content"><span class="msg-sender">Omni Mind</span><div class="msg-bubble"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div></div></div>`;
  messagesArea.appendChild(g);
  scrollBottom();
}
function removeTyping() { const el = document.getElementById('typing-group'); if (el) el.remove(); }

async function sendMessage() {
  if (!SESSION_ID) { openNewChatModal(); return; }
  const text = promptInput.value.trim();
  if (!text) return;
  appendMessage('user', text);
  promptInput.value = ''; promptInput.style.height = 'auto';
  showTyping();
  try {
    const res = await fetch(`/session/${SESSION_ID}/send/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    removeTyping();
    appendMessage('ai', data.ai_message, data.timestamp);
  } catch {
    removeTyping();
    appendMessage('ai', 'Ocorreu um erro. Tente novamente.');
  }
}

async function openNewChatModal() {
  const title = prompt('Nome do novo chat:') || 'Novo chat';
  const res = await fetch('/session/new/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ title }),
  });
  const data = await res.json();
  window.location.href = `/session/${data.session_id}/`;
}

function setChip(text) {
  promptInput.value = text;
  promptInput.focus();
  autoResize(promptInput);
}

/* ── COLLAPSIBLE SECTIONS ── */
function toggleSection(headerId) {
  const header = document.getElementById(headerId);
  const body   = header.nextElementSibling;
  const chevron = header.querySelector('.chevron');
  body.classList.toggle('open');
  chevron.classList.toggle('open');
}

/* ── GLOBAL PORTAL DROPDOWN ── */
let _ctxSessionId   = null;
let _ctxHighlighted = false;

// Create single portal dropdown in body
const dropdown = document.createElement('div');
dropdown.id = 'ctx-dropdown';
dropdown.innerHTML = `
  <div class="dropdown-opt" id="ctx-rename">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
    Renomear
  </div>
  <div class="dropdown-opt" id="ctx-pin">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
    </svg>
    Fixar
  </div>
  <div class="dropdown-divider"></div>
  <div class="dropdown-opt danger" id="ctx-delete">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14H6L5 6"/>
      <path d="M10 11v6M14 11v6"/>
      <path d="M9 6V4h6v2"/>
    </svg>
    Excluir
  </div>`;
document.body.appendChild(dropdown);

document.getElementById('ctx-rename').addEventListener('click', () => {
  closeDropdown();
  startRename(_ctxSessionId);
});
document.getElementById('ctx-pin').addEventListener('click', async () => {
  closeDropdown();
  await fetch(`/session/${_ctxSessionId}/toggle-highlight/`, {
    method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN }
  });
  window.location.reload();
});
document.getElementById('ctx-delete').addEventListener('click', async () => {
  closeDropdown();
  if (!confirm('Excluir este chat?')) return;
  await fetch(`/session/${_ctxSessionId}/delete/`, {
    method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN }
  });
  window.location.href = '/';
});

function openDropdown(e, sessionId, isHighlighted) {
  e.preventDefault();
  e.stopPropagation();
  _ctxSessionId   = sessionId;
  _ctxHighlighted = isHighlighted;

  // Update pin label
  const pinOpt = document.getElementById('ctx-pin');
  pinOpt.querySelector('svg').style.fill = isHighlighted ? 'currentColor' : 'none';
  pinOpt.childNodes[pinOpt.childNodes.length - 1].textContent = isHighlighted ? ' Desfixar' : ' Fixar';

  // Position near button
  const btn  = e.currentTarget;
  const rect = btn.getBoundingClientRect();
  dropdown.style.top  = (rect.bottom + 4) + 'px';
  dropdown.style.left = Math.min(rect.left, window.innerWidth - 170) + 'px';
  dropdown.classList.add('open');
}

function closeDropdown() { dropdown.classList.remove('open'); }

document.addEventListener('click', (e) => {
  if (!dropdown.contains(e.target)) closeDropdown();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDropdown(); });

/* ── RENAME INLINE ── */
function startRename(sessionId) {
  // Find the chat item
  const link = document.querySelector(`.chat-item[data-id="${sessionId}"]`);
  if (!link) return;
  const textEl = link.querySelector('.chat-item-text');
  const currentTitle = textEl.textContent.trim();

  // Replace span with input
  const input = document.createElement('input');
  input.className = 'chat-item-input';
  input.value = currentTitle;
  textEl.replaceWith(input);
  input.focus();
  input.select();

  async function commitRename() {
    const newTitle = input.value.trim() || currentTitle;
    // Restore text span
    const span = document.createElement('span');
    span.className = 'chat-item-text';
    span.textContent = newTitle;
    input.replaceWith(span);

    if (newTitle !== currentTitle) {
      await fetch(`/session/${sessionId}/rename/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
        body: JSON.stringify({ title: newTitle }),
      });
      // Update topbar if active
      const topbarTitle = document.querySelector('.topbar-title');
      if (topbarTitle && link.classList.contains('active')) topbarTitle.textContent = newTitle;
    }
  }

  input.addEventListener('blur', commitRename);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
    if (e.key === 'Escape') { input.value = currentTitle; input.blur(); }
  });
}

/* init */
scrollBottom();
