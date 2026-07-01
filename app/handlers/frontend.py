from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import get_settings

router = APIRouter(tags=["frontend"])


@router.get("/api/service-info")
async def service_info() -> dict:
    settings = get_settings()
    return {
        "service": settings.service_name,
        "status": "running",
        "environment": settings.environment,
        "otel_enabled": settings.otel_enabled,
        "traffic_generator_enabled": settings.enable_traffic_generator,
        "traffic_rate": settings.traffic_rate,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My Observability Service</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --surface-2: #eef2f6;
      --text: #1f2937;
      --muted: #5f6b7a;
      --line: #d9e0e8;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --danger: #b42318;
      --ok: #15803d;
      --warn: #b45309;
      --shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    a { color: inherit; text-decoration: none; }

    .app-shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 260px 1fr;
    }

    aside {
      background: #111827;
      color: #f9fafb;
      padding: 24px 18px;
      position: sticky;
      top: 0;
      height: 100vh;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 28px;
    }

    .brand-mark {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      background: linear-gradient(135deg, #14b8a6, #2563eb);
      display: grid;
      place-items: center;
      font-weight: 800;
      letter-spacing: 0;
    }

    .brand h1 {
      font-size: 16px;
      line-height: 1.2;
      margin: 0;
    }

    .brand p {
      margin: 2px 0 0;
      color: #cbd5e1;
      font-size: 12px;
    }

    .nav {
      display: grid;
      gap: 8px;
    }

    .nav a {
      min-height: 38px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 10px;
      border-radius: 8px;
      color: #d1d5db;
      font-size: 14px;
    }

    .nav a:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }

    .main {
      padding: 28px;
      display: grid;
      gap: 24px;
      align-content: start;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 56px;
    }

    .topbar h2 {
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }

    .topbar p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 14px;
    }

    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    button, .button {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      min-height: 38px;
      padding: 8px 12px;
      border-radius: 8px;
      font-weight: 650;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    button.primary, .button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }

    button.danger { color: var(--danger); }
    button:hover, .button:hover { box-shadow: var(--shadow); }

    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }

    .metric-card, .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .metric-card {
      padding: 16px;
      min-height: 112px;
      display: grid;
      align-content: space-between;
    }

    .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
      font-weight: 750;
    }

    .value {
      font-size: 28px;
      font-weight: 800;
      margin-top: 8px;
      line-height: 1.1;
    }

    .hint { color: var(--muted); font-size: 13px; }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
      font-weight: 700;
      background: #e8f7ee;
      color: var(--ok);
      white-space: nowrap;
    }

    .status-dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: currentColor;
    }

    .content-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
      gap: 18px;
      align-items: start;
    }

    .panel header {
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .panel h3 { margin: 0; font-size: 16px; }
    .panel-body { padding: 16px 18px; }

    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 14px;
    }

    th, td {
      padding: 11px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }

    .stack {
      display: grid;
      gap: 12px;
    }

    .endpoint-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 42px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }

    .endpoint-row:last-child { border-bottom: 0; }

    code {
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 2px 6px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 12px;
    }

    pre {
      margin: 0;
      background: #101828;
      color: #e5e7eb;
      border-radius: 8px;
      padding: 14px;
      min-height: 180px;
      max-height: 340px;
      overflow: auto;
      font-size: 12px;
      line-height: 1.5;
    }

    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    @media (max-width: 980px) {
      .app-shell { grid-template-columns: 1fr; }
      aside { position: static; height: auto; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .content-grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 620px) {
      .main { padding: 18px; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .actions { justify-content: flex-start; }
      .grid { grid-template-columns: 1fr; }
      table { font-size: 13px; }
      th, td { padding: 9px 6px; }
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside>
      <div class="brand">
        <div class="brand-mark">OS</div>
        <div>
          <h1>Observability Service</h1>
          <p id="environment">environment</p>
        </div>
      </div>
      <nav class="nav">
        <a href="/">Dashboard</a>
        <a href="/docs">API Docs</a>
        <a href="/metrics">Metrics</a>
        <a href="/health">Health</a>
      </nav>
    </aside>

    <main class="main">
      <section class="topbar">
        <div>
          <h2 id="service-name">My Observability Service</h2>
          <p>Operational view for API health, traffic simulation, and telemetry checks.</p>
        </div>
        <div class="actions">
          <span class="status-pill"><span class="status-dot"></span><span id="service-status">Checking</span></span>
          <a class="button primary" href="/docs">Open Docs</a>
        </div>
      </section>

      <section class="grid" aria-label="Service summary">
        <div class="metric-card">
          <div class="label">Health</div>
          <div class="value" id="health-value">--</div>
          <div class="hint">From /health</div>
        </div>
        <div class="metric-card">
          <div class="label">Orders</div>
          <div class="value" id="orders-value">--</div>
          <div class="hint">Current in-memory records</div>
        </div>
        <div class="metric-card">
          <div class="label">Customers</div>
          <div class="value" id="customers-value">--</div>
          <div class="hint">Sample customer data</div>
        </div>
        <div class="metric-card">
          <div class="label">Products</div>
          <div class="value" id="products-value">--</div>
          <div class="hint">Inventory catalog</div>
        </div>
      </section>

      <section class="content-grid">
        <div class="panel">
          <header>
            <h3>Orders</h3>
            <button onclick="refreshDashboard()">Refresh</button>
          </header>
          <div class="panel-body">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Items</th>
                </tr>
              </thead>
              <tbody id="orders-table">
                <tr><td colspan="5">Loading orders</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="stack">
          <div class="panel">
            <header><h3>Simulation</h3></header>
            <div class="panel-body stack">
              <div class="button-row">
                <button onclick="runSimulation('/simulate/normal')">Normal</button>
                <button onclick="runSimulation('/simulate/latency')">Latency</button>
                <button class="danger" onclick="runSimulation('/simulate/error')">Error</button>
                <button onclick="runSimulation('/simulate/cpu')">CPU</button>
                <button onclick="runSimulation('/simulate/memory')">Memory</button>
              </div>
              <pre id="simulation-output">Select a simulation to generate logs, metrics, and traces.</pre>
            </div>
          </div>

          <div class="panel">
            <header><h3>Telemetry Endpoints</h3></header>
            <div class="panel-body">
              <div class="endpoint-row"><code>/metrics</code><a class="button" href="/metrics">Open</a></div>
              <div class="endpoint-row"><code>/health</code><a class="button" href="/health">Open</a></div>
              <div class="endpoint-row"><code>/ready</code><a class="button" href="/ready">Open</a></div>
              <div class="endpoint-row"><code>/api/service-info</code><a class="button" href="/api/service-info">Open</a></div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    async function getJson(path) {
      const response = await fetch(path, { headers: { "accept": "application/json" } });
      const text = await response.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = { raw: text };
      }
      if (!response.ok) {
        throw { status: response.status, data };
      }
      return data;
    }

    function setText(id, value) {
      document.getElementById(id).textContent = value;
    }

    function renderOrders(orders) {
      const rows = orders.map((order) => `
        <tr>
          <td>${order.id}</td>
          <td>${order.customer_id}</td>
          <td>${order.status}</td>
          <td>$${Number(order.total).toFixed(2)}</td>
          <td>${order.items.map((item) => `${item.quantity} x product ${item.product_id}`).join(", ")}</td>
        </tr>
      `).join("");
      document.getElementById("orders-table").innerHTML = rows || "<tr><td colspan='5'>No orders found</td></tr>";
    }

    async function refreshDashboard() {
      try {
        const [info, health, orders, customers, products] = await Promise.all([
          getJson("/api/service-info"),
          getJson("/health"),
          getJson("/api/orders"),
          getJson("/api/customers"),
          getJson("/api/products")
        ]);

        setText("service-name", info.service);
        setText("environment", `${info.environment} environment`);
        setText("service-status", info.status);
        setText("health-value", health.status);
        setText("orders-value", orders.length);
        setText("customers-value", customers.length);
        setText("products-value", products.length);
        renderOrders(orders);
      } catch (error) {
        setText("service-status", "degraded");
        document.getElementById("orders-table").innerHTML = "<tr><td colspan='5'>Unable to load dashboard data</td></tr>";
      }
    }

    async function runSimulation(path) {
      const output = document.getElementById("simulation-output");
      output.textContent = `Calling ${path} ...`;
      try {
        const data = await getJson(path);
        output.textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        output.textContent = JSON.stringify(error, null, 2);
      } finally {
        refreshDashboard();
      }
    }

    refreshDashboard();
    setInterval(refreshDashboard, 15000);
  </script>
</body>
</html>"""

