let TOKEN = localStorage.getItem("sveta_admin_token") || "";

const tokenInput = document.getElementById("token");
const app = document.getElementById("app");

function riskClass(level) {
  return `risk-${level}`;
}

async function authedFetch(path) {
  const resp = await fetch(path, { headers: { "X-Admin-Token": TOKEN } });
  if (!resp.ok) throw new Error(`${resp.status}`);
  return resp.json();
}

async function loadDashboard() {
  const stats = await authedFetch("/api/admin/dashboard");
  document.getElementById("stats").innerHTML = `
    <div>Всего сессий<strong>${stats.total_sessions}</strong></div>
    <div>Средний trust<strong>${stats.avg_trust}</strong></div>
    <div>Средняя suspicion<strong>${stats.avg_suspicion}</strong></div>
    <div>Средний risk<strong>${stats.avg_risk}</strong></div>
  `;
  const flagRows = Object.entries(stats.red_flag_frequency)
    .map(([code, count]) => `<tr><td>${code}</td><td>${count}</td></tr>`)
    .join("");
  document.querySelector("#flagTable tbody").innerHTML = flagRows || "<tr><td colspan=2>Нет данных</td></tr>";
}

async function loadSessions() {
  const sessions = await authedFetch("/api/admin/sessions");
  const rows = sessions.map((s) => `
    <tr class="session-row" data-id="${s.session_id}">
      <td>${s.session_id.slice(0, 8)}</td>
      <td>${s.day}</td>
      <td>${s.stage}</td>
      <td>${s.trust.toFixed(0)}</td>
      <td>${s.attraction.toFixed(0)}</td>
      <td>${s.suspicion.toFixed(0)}</td>
      <td>${s.risk.toFixed(0)}</td>
      <td>${new Date(s.updated_at).toLocaleString()}</td>
    </tr>
  `).join("");
  const tbody = document.querySelector("#sessionsTable tbody");
  tbody.innerHTML = rows || "<tr><td colspan=8>Нет сессий</td></tr>";
  tbody.querySelectorAll(".session-row").forEach((row) => {
    row.addEventListener("click", () => loadDetail(row.dataset.id));
  });
}

async function loadDetail(sessionId) {
  const detail = await authedFetch(`/api/admin/sessions/${sessionId}`);
  const chat = detail.messages.map((m) => `<div class="m ${m.role}">[день ${m.day}] <strong>${m.role}:</strong> ${m.content}</div>`).join("");
  const flags = (detail.state.red_flags || []).map((f) => `<span class="badge">${f}</span>`).join("") || "—";
  const signals = (detail.state.manipulation_signals || []).map((f) => `<span class="badge">${f}</span>`).join("") || "—";
  const events = detail.research_events.map((e) => `
    <div>день ${e.day} — <strong>${e.event}</strong> (${e.user_action || "auto"}):
    trust ${e.trust_before}→${e.trust_after}, suspicion ${e.suspicion_before}→${e.suspicion_after}, risk ${e.risk_before}→${e.risk_after}</div>
  `).join("") || "—";

  document.getElementById("detail").innerHTML = `
    <h3>Сессия ${sessionId}</h3>
    <div class="chat-log">${chat}</div>
    <p><strong>Red flags:</strong> ${flags}</p>
    <p><strong>Manipulation signals:</strong> ${signals}</p>
    <p><strong>Research events:</strong></p>
    ${events}
    <p><strong>Полное состояние:</strong></p>
    <pre>${JSON.stringify(detail.state, null, 2)}</pre>
  `;
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadSessions()]);
}

document.getElementById("saveToken").addEventListener("click", async () => {
  TOKEN = tokenInput.value.trim();
  localStorage.setItem("sveta_admin_token", TOKEN);
  try {
    await refreshAll();
    app.classList.remove("hidden");
  } catch {
    alert("Неверный токен или сервер недоступен");
  }
});

if (TOKEN) {
  tokenInput.value = TOKEN;
  refreshAll().then(() => app.classList.remove("hidden")).catch(() => {});
}
