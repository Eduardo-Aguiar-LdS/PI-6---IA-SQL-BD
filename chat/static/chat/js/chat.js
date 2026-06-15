const CSRF_TOKEN   = window.CSRF_TOKEN;
const messagesArea = document.getElementById('messages-area');
const promptInput  = document.getElementById('prompt-input');

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function scrollBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function nowTime() {
  const d = new Date();
  return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}

function clearEmptyState() {
  const empty = messagesArea.querySelector('.empty-state');
  if (empty) empty.remove();
}

function appendMessage(role, content, time) {
  const isUser = role === 'user';
  const group  = document.createElement('div');
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
  g.className = 'message-group';
  g.id = 'typing-group';
  g.innerHTML = `
    <div class="message ai">
      <div class="msg-avatar ai">O</div>
      <div class="msg-content">
        <span class="msg-sender">Omni Mind</span>
        <div class="msg-bubble">
          <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      </div>
    </div>`;
  messagesArea.appendChild(g);
  scrollBottom();
}

function removeTyping() {
  const el = document.getElementById('typing-group');
  if (el) el.remove();
}

async function sendMessage() {
  const text = promptInput.value.trim();
  if (!text) return;

  clearEmptyState();
  appendMessage('user', text);
  promptInput.value = '';
  promptInput.style.height = 'auto';
  showTyping();

  try {
    const res = await fetch('/chat/perguntar/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    removeTyping();
    appendMessage('ai', data.ai_message, data.timestamp);
  } catch {
    removeTyping();
    appendMessage('ai', 'Erro ao conectar com a IA. Verifique se o Ollama está rodando.');
  }
}

function setChip(text) {
  promptInput.value = text;
  promptInput.focus();
  autoResize(promptInput);
}