from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SREAgent</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8f4;
      --panel: #ffffff;
      --ink: #1f2328;
      --muted: #667085;
      --line: #d7dbcf;
      --accent: #0f766e;
      --critical: #b42318;
      --high: #b54708;
      --medium: #a15c07;
      --low: #175cd3;
      --info: #475467;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 2;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 420px) 1fr;
      min-height: calc(100vh - 68px);
    }
    .toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    input, select, button {
      height: 36px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      padding: 0 10px;
      font: inherit;
    }
    button {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      cursor: pointer;
      font-weight: 650;
    }
    .list {
      border-right: 1px solid var(--line);
      padding: 16px;
      overflow: auto;
      max-height: calc(100vh - 68px);
    }
    .detail {
      padding: 18px 22px;
      overflow: auto;
      max-height: calc(100vh - 68px);
    }
    .incident {
      width: 100%;
      text-align: left;
      background: var(--panel);
      color: var(--ink);
      border: 1px solid var(--line);
      border-left: 5px solid var(--info);
      border-radius: 6px;
      padding: 12px;
      margin: 0 0 10px;
      cursor: pointer;
    }
    .incident.active {
      border-color: var(--accent);
      border-left-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(15, 118, 110, .14);
    }
    .incident[data-severity="critical"] { border-left-color: var(--critical); }
    .incident[data-severity="high"] { border-left-color: var(--high); }
    .incident[data-severity="medium"] { border-left-color: var(--medium); }
    .incident[data-severity="low"] { border-left-color: var(--low); }
    .incident-title {
      display: block;
      font-weight: 700;
      margin-bottom: 6px;
      overflow-wrap: anywhere;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      background: #fbfcf8;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .metric, .section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
    }
    .metric b {
      display: block;
      font-size: 20px;
      line-height: 1.2;
    }
    .metric span, .empty, .muted {
      color: var(--muted);
    }
    .section {
      margin-bottom: 12px;
    }
    .section h2 {
      margin: 0 0 8px;
      font-size: 15px;
      letter-spacing: 0;
    }
    .section p {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .evidence {
      display: grid;
      gap: 8px;
    }
    .evidence-item {
      border-top: 1px solid var(--line);
      padding-top: 8px;
    }
    @media (max-width: 860px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .list {
        border-right: 0;
        border-bottom: 1px solid var(--line);
        max-height: 42vh;
      }
      .detail { max-height: none; }
      .summary-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }
  </style>
</head>
<body>
  <header>
    <h1>SREAgent</h1>
    <div class="toolbar">
      <input id="token" type="password" autocomplete="off" placeholder="X-API-Token">
      <select id="status">
        <option value="">Todos</option>
        <option value="analyzed">Analisados</option>
        <option value="observed">Observados</option>
        <option value="resolved">Resolvidos</option>
        <option value="ignored">Ignorados</option>
      </select>
      <button id="refresh" type="button">Atualizar</button>
    </div>
  </header>
  <main>
    <section class="list" id="list"></section>
    <section class="detail" id="detail"></section>
  </main>
  <script>
    const list = document.querySelector("#list");
    const detail = document.querySelector("#detail");
    const tokenInput = document.querySelector("#token");
    const statusFilter = document.querySelector("#status");
    const refreshButton = document.querySelector("#refresh");
    let incidents = [];
    let selectedId = null;

    tokenInput.value = localStorage.getItem("sreagent_api_token") || "";
    tokenInput.addEventListener("change", () => {
      localStorage.setItem("sreagent_api_token", tokenInput.value);
    });
    statusFilter.addEventListener("change", loadIncidents);
    refreshButton.addEventListener("click", loadIncidents);

    function headers() {
      const token = tokenInput.value.trim();
      return token ? {"X-API-Token": token} : {};
    }

    function fmtDate(value) {
      return new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(new Date(value));
    }

    function html(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[char]));
    }

    function counts(items) {
      return items.reduce((acc, item) => {
        acc[item.severity] = (acc[item.severity] || 0) + 1;
        return acc;
      }, {});
    }

    function renderList() {
      if (!incidents.length) {
        list.innerHTML = '<p class="empty">Nenhum incidente registrado.</p>';
        detail.innerHTML = "";
        return;
      }
      if (!selectedId || !incidents.some(item => item.id === selectedId)) {
        selectedId = incidents[0].id;
      }
      list.innerHTML = incidents.map(item => `
        <button class="incident ${item.id === selectedId ? "active" : ""}"
          data-id="${html(item.id)}" data-severity="${html(item.severity)}">
          <span class="incident-title">${html(item.title)}</span>
          <span class="meta">
            <span class="pill">${html(item.service)}</span>
            <span class="pill">${html(item.environment)}</span>
            <span class="pill">${html(item.status)}</span>
            <span>${fmtDate(item.created_at)}</span>
          </span>
        </button>
      `).join("");
      document.querySelectorAll(".incident").forEach(button => {
        button.addEventListener("click", () => {
          selectedId = button.dataset.id;
          renderList();
          renderDetail();
        });
      });
      renderDetail();
    }

    function renderDetail() {
      const item = incidents.find(record => record.id === selectedId);
      if (!item) {
        detail.innerHTML = "";
        return;
      }
      const stats = counts(incidents);
      const evidence = item.result.evidence || [];
      detail.innerHTML = `
        <div class="summary-grid">
          <div class="metric"><b>${incidents.length}</b><span>recentes</span></div>
          <div class="metric"><b>${stats.critical || 0}</b><span>critical</span></div>
          <div class="metric"><b>${stats.high || 0}</b><span>high</span></div>
          <div class="metric"><b>${stats.medium || 0}</b><span>medium</span></div>
        </div>
        <div class="section">
          <h2>${html(item.title)}</h2>
          <p class="muted">${fmtDate(item.created_at)} · ${html(item.source)} · ${html(item.dedup_key)}</p>
        </div>
        <div class="section">
          <h2>Hipótese</h2>
          <p>${html(item.primary_hypothesis)}</p>
        </div>
        <div class="section">
          <h2>Diagnóstico</h2>
          <p>${html(item.result.diagnosis.probable_failure_type)} · ${html(item.confidence)} · ${html(item.correlation_rule)}</p>
        </div>
        <div class="section">
          <h2>Lacunas</h2>
          <p>${html((item.result.correlation.information_gaps || []).join(", ") || "nenhuma")}</p>
        </div>
        <div class="section">
          <h2>Evidências</h2>
          <div class="evidence">
            ${evidence.map(ev => `
              <div class="evidence-item">
                <b>${html(ev.source)} · ${html(ev.kind)}</b>
                <p>${html(ev.summary)}</p>
              </div>
            `).join("") || '<p class="empty">Sem evidências coletadas.</p>'}
          </div>
        </div>
      `;
    }

    async function loadIncidents() {
      const params = new URLSearchParams({limit: "50"});
      if (statusFilter.value) params.set("status", statusFilter.value);
      const response = await fetch(`/incidents/recent?${params}`, {headers: headers()});
      if (!response.ok) {
        list.innerHTML = '<p class="empty">Falha ao carregar incidentes.</p>';
        detail.innerHTML = "";
        return;
      }
      const payload = await response.json();
      incidents = payload.incidents || [];
      renderList();
    }

    loadIncidents();
  </script>
</body>
</html>
        """
    )
