const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const pinEl = document.getElementById("pin");

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

function addBubble(role, content, createdAt) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = content;
  const time = document.createElement("span");
  time.className = "time";
  time.textContent = formatTime(createdAt || new Date().toISOString());
  div.appendChild(time);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function headers() {
  const h = { "Content-Type": "application/json" };
  const pin = pinEl.value.trim();
  if (pin) h["X-Pilot-Pin"] = pin;
  return h;
}

async function loadHistory() {
  const res = await fetch("/api/chat/history", { headers: headers() });
  if (!res.ok) return;
  const items = await res.json();
  messagesEl.innerHTML = "";
  items.forEach((m) => addBubble(m.role, m.content, m.created_at));
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;
  sendBtn.disabled = true;
  inputEl.value = "";
  addBubble("user", text);

  const typing = document.createElement("div");
  typing.className = "bubble assistant typing";
  typing.textContent = "Hermes is typing…";
  messagesEl.appendChild(typing);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ message: text }),
    });
    typing.remove();
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      addBubble("assistant", err.detail || "Something went wrong. Please try again.");
      return;
    }
    const data = await res.json();
    addBubble("assistant", data.reply, data.sent_at);
  } catch {
    typing.remove();
    addBubble("assistant", "Network error — check your connection and try again.");
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

loadHistory().then(() => {
  if (!messagesEl.children.length) {
    addBubble("assistant", "Hello! 👋 Type Hi to get started.");
  }
});

async function pollNotifications() {
  try {
    const res = await fetch("/api/notifications/poll", { headers: headers() });
    if (!res.ok) return;
    const items = await res.json();
    items.forEach((n) => addBubble("assistant", n.content, n.created_at));
  } catch {
    /* ignore polling errors */
  }
}

setInterval(pollNotifications, 15000);
pollNotifications();
