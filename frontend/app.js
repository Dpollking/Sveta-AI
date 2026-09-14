const API_BASE = window.SVETA_API_BASE || "";
const SESSION_ID = localStorage.getItem("sveta_session_id") || crypto.randomUUID();
localStorage.setItem("sveta_session_id", SESSION_ID);

const messagesEl = document.getElementById("messages");
const dayEl = document.getElementById("day");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const reportBtn = document.getElementById("reportBtn");
const reportEl = document.getElementById("report");

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function addMedia(container, media) {
  media.forEach((m) => {
    const box = document.createElement("div");
    box.className = "media-placeholder" + (m.blurred ? " blurred" : "");
    box.textContent = m.blurred ? "[изображение скрыто до подтверждения]" : `[${m.description}]`;
    container.appendChild(box);
  });
}

async function sendMessage(text) {
  addMessage("user", text);
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: SESSION_ID, message: text }),
  });
  const data = await resp.json();
  const el = addMessage("assistant", data.reply);
  if (data.media && data.media.length) addMedia(el, data.media);
  dayEl.textContent = `день ${data.day}`;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendMessage(text);
});

reportBtn.addEventListener("click", async () => {
  const resp = await fetch(`${API_BASE}/api/session/${SESSION_ID}/report`);
  if (!resp.ok) return;
  const data = await resp.json();
  const findings = (data.findings || []).map((f) => `<li>${f}</li>`).join("");
  reportEl.innerHTML = `
    <h3>Образовательный отчёт (день ${data.day})</h3>
    <div>Уровень риска: <strong>${data.risk_level}</strong></div>
    ${findings ? `<ul>${findings}</ul>` : "<p>Явных красных флагов не обнаружено.</p>"}
    <p>${data.recommendation}</p>
  `;
  reportEl.classList.remove("hidden");
});

fetch(`${API_BASE}/api/session/${SESSION_ID}`)
  .then((r) => r.json())
  .then((data) => { dayEl.textContent = `день ${data.day}`; });
