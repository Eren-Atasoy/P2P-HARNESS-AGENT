/**
 * Prompt2Product Dashboard SPA Logic (docs/12 §2.A, docs/08 Faz 10)
 * Fully interactive control center for autonomous runs, human steering, and approvals.
 */

const state = {
  currentTab: 'overview',
  data: {
    state: null,
    tasks: [],
    events: [],
    approvals: [],
    connections: [],
    retro: [],
  },
  selectedTask: null,
  theme: localStorage.getItem('p2p-theme') || 'dark',
  isBusy: false,
};

// --- Toast Notifications ---
function showToast(message, duration = 3500) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// --- Theme Management ---
function initTheme() {
  document.documentElement.setAttribute('data-theme', state.theme);
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.textContent = state.theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    themeToggle.addEventListener('click', () => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', state.theme);
      localStorage.setItem('p2p-theme', state.theme);
      themeToggle.textContent = state.theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    });
  }
}

// --- Data Fetching ---
let isFetching = false;
async function fetchData() {
  if (isFetching) return;
  isFetching = true;
  try {
    const [stateRes, tasksRes, eventsRes, approvalsRes, connsRes, retroRes] = await Promise.all([
      fetch('/api/state').then(r => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('/api/tasks').then(r => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('/api/events').then(r => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('/api/approvals').then(r => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('/api/connections').then(r => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('/api/retro').then(r => r.ok ? r.json() : {}).catch(() => ({})),
    ]);

    if (stateRes && stateRes.state) state.data.state = stateRes.state;
    if (tasksRes && tasksRes.tasks) state.data.tasks = tasksRes.tasks;
    if (eventsRes && eventsRes.events) state.data.events = eventsRes.events;
    if (approvalsRes && approvalsRes.approvals) state.data.approvals = approvalsRes.approvals;
    if (connsRes && connsRes.connections) state.data.connections = connsRes.connections;
    if (retroRes && retroRes.recommendations) state.data.retro = retroRes.recommendations;

    // Keep selectedTask updated if exists
    if (state.selectedTask) {
      const updated = state.data.tasks.find(t => t.id === state.selectedTask.id);
      if (updated) state.selectedTask = updated;
    }

    render();
  } catch (err) {
    // Gracefully ignore network cancel/abort
  } finally {
    isFetching = false;
  }
}

// --- Navigation ---
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      const tab = item.getAttribute('data-tab');
      if (tab) {
        state.currentTab = tab;
        navItems.forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        render();
      }
    });
  });
}

// --- Renderers for 7 Views ---

function renderOverview() {
  const tasks = state.data.tasks;
  const decisions = state.data.state?.decisions || [];
  const completed = tasks.filter(t => t.status === 'COMPLETED' || t.status === 'APPROVED').length;
  const inProgress = tasks.filter(t => t.status === 'RUNNING' || t.status === 'IMPLEMENTING').length;
  const blocked = tasks.filter(t => t.status === 'BLOCKED' || t.status === 'ESCALATED' || t.status === 'REJECTED').length;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Run Overview</h1>
        <p class="page-subtitle">Autonomous execution state, interactive console, and decision lineage</p>
      </div>
      <div style="display: flex; gap: 8px; align-items: center;">
        <span class="badge badge-success">${completed} Completed</span>
        <span class="badge badge-running">${inProgress} Running</span>
        ${blocked > 0 ? `<span class="badge badge-danger">${blocked} Blocked</span>` : ''}
      </div>
    </div>

    <!-- Interactive Command & Run Console -->
    <div class="panel" style="border-color: var(--accent-brand-border); background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-raised) 100%);">
      <div class="panel-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--accent-brand);"></span>
          <h2 class="panel-title" style="color: var(--text-primary); font-size: 15px;">Interactive Command & Run Console</h2>
        </div>
        <span class="brand-badge">P2P v1.0 LIVE</span>
      </div>

      <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">
        Doğrudan tarayıcı üzerinden doğal dil promptu verip projeyi planlatabilir (G1 → G2 → G3) ve otonom döngüyü başlatabilirsiniz.
      </p>

      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div>
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;">
            PROMPT (PROJE TANIMI):
          </label>
          <textarea id="run-prompt" rows="2" class="input-control" placeholder="Örn: FastAPI ve SQLite ile multi-user Todo REST API'si oluştur, JWT yetkilendirme ve CRUD uçları ekle...">FastAPI ve SQLite ile multi-user Todo REST API'si oluştur, JWT yetkilendirme ve CRUD uçları ekle</textarea>
        </div>

        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 200px;">
            <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;">
              BLUEPRINT:
            </label>
            <select id="run-blueprint" class="input-control">
              <option value="fastapi">FastAPI (Async REST, Pydantic, pytest)</option>
              <option value="python_cli">Python CLI (Click/Argparse, Subcommands)</option>
            </select>
          </div>

          <div style="flex: 1; min-width: 200px;">
            <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;">
              AUTONOMY LEVEL:
            </label>
            <select id="run-autonomy" class="input-control">
              <option value="guarded">Guarded (High-Risk Onay Kapılı)</option>
              <option value="full">Full (Tam Otonom Yürütme)</option>
            </select>
          </div>
        </div>

        <div style="display: flex; gap: 12px; align-items: center; margin-top: 8px; flex-wrap: wrap;">
          <button class="btn btn-brand" id="btn-plan-project" onclick="triggerPlanProject()">
            ⚡ Plan Project (G1 → G2 → G3)
          </button>
          <button class="btn btn-success" id="btn-start-run" onclick="triggerStartRun()">
            ▶ Start Autonomous Run
          </button>
          <button class="btn btn-secondary" onclick="simulateApprovalRequest()">
            🛡️ Test Approval / Steer
          </button>
          <span id="run-status-text" style="font-size: 12px; color: var(--accent-brand); font-family: var(--font-mono); margin-left: auto;"></span>
        </div>
      </div>
    </div>

    <!-- Planning Chain Gates -->
    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Planning Chain Gates</h2>
        <span style="font-size: 12px; color: var(--text-secondary);">G1: Discovery, G2: Architecture, G3: Decomposition</span>
      </div>
      <div style="display: flex; gap: 16px; flex-wrap: wrap;">
        <div style="flex: 1; padding: 12px; background: var(--bg-raised); border-radius: 6px;">
          <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">GATE G1</div>
          <div style="font-weight: 600; margin-top: 4px;">Discovery & Scope</div>
          <div style="margin-top: 8px;"><span class="badge badge-success">PASS</span></div>
        </div>
        <div style="flex: 1; padding: 12px; background: var(--bg-raised); border-radius: 6px;">
          <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">GATE G2</div>
          <div style="font-weight: 600; margin-top: 4px;">Architecture & ADRs</div>
          <div style="margin-top: 8px;"><span class="badge badge-success">PASS</span></div>
        </div>
        <div style="flex: 1; padding: 12px; background: var(--bg-raised); border-radius: 6px;">
          <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">GATE G3</div>
          <div style="font-weight: 600; margin-top: 4px;">Task Decomposition</div>
          <div style="margin-top: 8px;"><span class="badge badge-success">PASS</span></div>
        </div>
      </div>
    </div>

    <!-- Governance & Decisions -->
    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Governance & Autonomous Decisions</h2>
        <span style="font-size: 12px; color: var(--text-secondary);">Decisions made in user's absence (docs/12 §2.A)</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Decision ID</th>
            <th>Kind</th>
            <th>Question</th>
            <th>Chosen Option</th>
            <th>Decided By</th>
          </tr>
        </thead>
        <tbody>
          ${decisions.length === 0 ? '<tr><td colspan="5" style="color: var(--text-tertiary);">No decisions recorded yet. Plan a project above to generate decisions.</td></tr>' : ''}
          ${decisions.map(d => `
            <tr>
              <td class="tabular"><strong>${d.id}</strong></td>
              <td>${d.kind}</td>
              <td>${d.question}</td>
              <td style="color: var(--accent-brand); font-weight: 500;">${d.chosen}</td>
              <td>
                ${d.decided_by === 'default'
                  ? '<span class="default-decision-tag">decided_by=default</span>'
                  : '<span class="badge badge-success">human</span>'}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderTaskGraph() {
  const waves = state.data.state?.waves || [];
  const allTasks = state.data.tasks;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Task Graph & Concurrency</h1>
        <p class="page-subtitle">Directed Acyclic Graph executed across horizontal parallel waves</p>
      </div>
      <button class="btn btn-brand" onclick="navigateToTab('detail')">Inspect Task Details →</button>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Execution Waves</h2>
        <span style="font-size: 12px; color: var(--text-tertiary);">Click any task node to view/edit contract</span>
      </div>

      ${allTasks.length === 0 ? `
        <div style="padding: 24px; text-align: center; color: var(--text-tertiary);">
          <p>No tasks generated yet.</p>
          <button class="btn btn-brand" style="margin-top: 12px;" onclick="navigateToTab('overview')">Go to Overview & Plan Project</button>
        </div>
      ` : (waves.length === 0 ? `
        <div class="wave-band">
          <div class="wave-title">WAVE 1 (PARALLEL EXECUTION BATCH)</div>
          <div class="wave-tasks">
            ${allTasks.map(t => `
              <div class="task-node risk-${t.risk || 'low'}" onclick="viewTaskDetail('${t.id}')">
                <span class="tabular"><strong>${t.id}</strong></span>
                <span>${t.title}</span>
                <span class="badge badge-${t.status === 'COMPLETED' ? 'success' : (t.status === 'BLOCKED' ? 'danger' : 'running')}">${t.status || 'PENDING'}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : waves.map((wave, idx) => `
        <div class="wave-band">
          <div class="wave-title">WAVE ${idx + 1} (${wave.length} PARALLEL TASKS)</div>
          <div class="wave-tasks">
            ${wave.map(tid => {
              const t = allTasks.find(item => item.id === tid) || { id: tid, title: tid, risk: 'low' };
              return `
                <div class="task-node risk-${t.risk || 'low'}" onclick="viewTaskDetail('${t.id}')">
                  <span class="tabular"><strong>${t.id}</strong></span>
                  <span>${t.title}</span>
                  <span class="badge badge-${t.status === 'COMPLETED' ? 'success' : 'running'}">${t.status || 'PENDING'}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `).join(''))}
    </div>
  `;
}

function renderTaskDetail() {
  const task = state.selectedTask || state.data.tasks[0];
  if (!task) {
    return `
      <div class="panel" style="text-align: center; padding: 32px;">
        <h3 style="font-size: 16px; margin-bottom: 8px;">No Task Available</h3>
        <p style="color: var(--text-tertiary); margin-bottom: 16px;">Plan a project from the Overview tab to create tasks.</p>
        <button class="btn btn-brand" onclick="navigateToTab('overview')">Go to Overview</button>
      </div>
    `;
  }

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Task Detail: ${task.id}</h1>
        <p class="page-subtitle">${task.title}</p>
      </div>
      <div style="display: flex; gap: 8px; align-items: center;">
        <span class="badge badge-${task.risk === 'high' ? 'danger' : 'running'}">Risk: ${task.risk}</span>
        <span class="badge badge-${task.status === 'COMPLETED' ? 'success' : (task.status === 'BLOCKED' ? 'danger' : 'running')}">${task.status || 'PENDING'}</span>
      </div>
    </div>

    <!-- Interactive Task Controls -->
    <div class="panel" style="border-color: var(--accent-brand-border);">
      <div class="panel-header">
        <h2 class="panel-title">Interactive Task Controls & Steering</h2>
        <span style="font-size: 12px; color: var(--text-secondary);">Direct state mutation & directive injection</span>
      </div>

      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px;">
        <button class="btn btn-success" onclick="updateTaskStatus('${task.id}', 'COMPLETED')">✓ Mark Completed</button>
        <button class="btn btn-brand" onclick="updateTaskStatus('${task.id}', 'RUNNING')">▶ Set Running</button>
        <button class="btn btn-danger" onclick="updateTaskStatus('${task.id}', 'BLOCKED')">⏸ Mark Blocked</button>
        <button class="btn btn-secondary" onclick="toggleTaskApproval('${task.id}', ${!task.human_approval})">
          ${task.human_approval ? '🔓 Remove Approval Gate' : '🔒 Require Human Approval'}
        </button>
      </div>

      <div>
        <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;">
          INJECT STEER DIRECTIVE (AGENT TALİMATI):
        </label>
        <div style="display: flex; gap: 8px;">
          <input type="text" id="task-directive-input" class="input-control" placeholder="Örn: SQLite yerine InMemory database kullan, testleri pytest-asyncio ile yaz...">
          <button class="btn btn-brand" onclick="injectTaskDirective('${task.id}')">Inject Directive</button>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Task Contract Specification</h2>
        <span style="font-size: 12px; font-family: var(--font-mono); color: var(--text-tertiary);">${task.id}.json</span>
      </div>
      <div class="code-block">${JSON.stringify(task, null, 2)}</div>
    </div>
  `;
}

function renderEventStream() {
  const events = state.data.events;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Event Stream</h1>
        <p class="page-subtitle">Immutable append-only audit log (.p2p/events.jsonl)</p>
      </div>
      <span class="tabular" style="color: var(--text-tertiary);">${events.length} total events</span>
    </div>

    <div class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Type</th>
            <th>Task ID</th>
            <th>Timestamp</th>
            <th>Data Summary</th>
          </tr>
        </thead>
        <tbody>
          ${events.length === 0 ? '<tr><td colspan="5" style="color: var(--text-tertiary);">No events recorded yet.</td></tr>' : ''}
          ${events.map(e => `
            <tr>
              <td class="tabular">#${e.event_id || '-'}</td>
              <td><span class="badge badge-running">${e.type}</span></td>
              <td class="tabular"><strong>${e.task_id || '-'}</strong></td>
              <td class="tabular" style="color: var(--text-tertiary);">${new Date(e.timestamp).toLocaleTimeString()}</td>
              <td class="tabular" style="font-size: 11px;">${JSON.stringify(e.data || {})}</td>
            </tr>
          `).reverse().slice(0, 50).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderApprovals() {
  const approvals = state.data.approvals.filter(a => a.human_approval || a.status === 'PENDING_APPROVAL');

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Human Approvals & Steering</h1>
        <p class="page-subtitle">Decisions requiring human intervention (Gate G, High Risk, or Escalations)</p>
      </div>
      <button class="btn btn-secondary" onclick="simulateApprovalRequest()">+ Simulate High-Risk Task</button>
    </div>

    ${approvals.length === 0 ? `
      <div class="panel" style="text-align: center; padding: 32px;">
        <p style="color: var(--status-success); font-weight: 600; font-size: 15px; margin-bottom: 8px;">
          ✓ No pending human approvals.
        </p>
        <p style="color: var(--text-secondary); font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
          Otonom agent döngüsü engelsiz çalışıyor. İnsan onay mekanizmasını ve steering (yön verme) özelliğini hemen denemek için aşağıdaki simülasyon butonuna basabilirsiniz.
        </p>
        <button class="btn btn-brand" onclick="simulateApprovalRequest()">Simulate Approval Request</button>
      </div>
    ` : approvals.map(app => `
      <div class="panel" style="border-left: 3px solid var(--status-gated);">
        <div class="panel-header">
          <div>
            <h3 style="font-size: 16px; font-weight: 600;">${app.id}: ${app.title}</h3>
            <span style="color: var(--text-secondary); font-size: 13px;">${app.intent || 'High-risk automated execution awaiting confirmation'}</span>
          </div>
          <span class="badge badge-gated">AWAITING APPROVAL</span>
        </div>

        <div style="margin: 16px 0;">
          <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 6px;">ALLOWED PATHS:</div>
          <div class="code-block">${(app.allowed_paths || []).join(', ') || 'None specified'}</div>
          ${app.notes ? `<div style="margin-top: 8px; font-size: 12px; color: var(--accent-brand);"><strong>NOTES / DIRECTIVES:</strong> ${app.notes}</div>` : ''}
        </div>

        <div style="display: flex; gap: 12px; align-items: center; margin-top: 16px; flex-wrap: wrap;">
          <button class="btn btn-success" onclick="submitApproval('${app.id}', 'approve')">Approve Task</button>
          <button class="btn btn-danger" onclick="submitApproval('${app.id}', 'reject')">Reject</button>
          <input type="text" id="steer-${app.id}" placeholder="Provide steer feedback (e.g. 'Use staging database first')..." class="input-control" style="flex: 1; min-width: 250px;">
          <button class="btn btn-brand" onclick="submitApproval('${app.id}', 'steer')">Steer Agent</button>
        </div>
      </div>
    `).join('')}
  `;
}

function renderConnections() {
  const conns = state.data.connections;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Connections & Model Health</h1>
        <p class="page-subtitle">Runtime adapters and external provider diagnostics (p2p doctor)</p>
      </div>
    </div>

    <div class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th>Connection ID</th>
            <th>Kind</th>
            <th>Available</th>
            <th>Authenticated</th>
            <th>Version / Adapter</th>
            <th>Streaming</th>
          </tr>
        </thead>
        <tbody>
          ${conns.map(c => `
            <tr>
              <td><strong>${c.id}</strong></td>
              <td><span class="badge badge-running">${c.kind}</span></td>
              <td><span class="badge badge-${c.available ? 'success' : 'danger'}">${c.available ? 'ONLINE' : 'OFFLINE'}</span></td>
              <td><span class="badge badge-${c.authenticated ? 'success' : 'warning'}">${c.authenticated ? 'YES' : 'NO'}</span></td>
              <td class="tabular">${c.version || '-'}</td>
              <td>${c.can_stream ? 'Yes' : 'No'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderRetro() {
  const recs = state.data.retro;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Retrospective & Rule Proposals</h1>
        <p class="page-subtitle">Synthesized rules and gate proposals from failure patterns (p2p retro)</p>
      </div>
      <button class="btn btn-brand" onclick="scanRetro()">⚡ Run Retro Scan</button>
    </div>

    <div class="panel">
      ${recs.length === 0 ? `
        <div style="padding: 24px; text-align: center;">
          <p style="color: var(--status-success); font-weight: 500; margin-bottom: 12px;">✓ Clean run history: No recurring failure patterns detected.</p>
          <button class="btn btn-secondary" onclick="scanRetro()">Scan Event Store for Patterns</button>
        </div>
      ` : `
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Kind</th>
              <th>Pattern</th>
              <th>Frequency</th>
              <th>Proposed Recommendation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${recs.map(r => `
              <tr>
                <td class="tabular"><strong>${r.id}</strong></td>
                <td><span class="badge badge-warning">${r.kind}</span></td>
                <td>${r.pattern}</td>
                <td class="tabular">${r.count}x</td>
                <td>${r.recommendation}</td>
                <td>
                  <button class="btn btn-brand" onclick="applyRetro('${r.id}')" style="font-size: 11px; padding: 4px 8px;">Apply</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `}
    </div>
  `;
}

// --- Main Render Dispatcher ---
function render() {
  const content = document.getElementById('main-content');
  if (!content) return;

  switch (state.currentTab) {
    case 'overview': content.innerHTML = renderOverview(); break;
    case 'graph': content.innerHTML = renderTaskGraph(); break;
    case 'detail': content.innerHTML = renderTaskDetail(); break;
    case 'events': content.innerHTML = renderEventStream(); break;
    case 'approvals': content.innerHTML = renderApprovals(); break;
    case 'connections': content.innerHTML = renderConnections(); break;
    case 'retro': content.innerHTML = renderRetro(); break;
    default: content.innerHTML = renderOverview();
  }
}

// --- User Actions & Operations ---

window.navigateToTab = function(tabName) {
  state.currentTab = tabName;
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(n => {
    n.classList.toggle('active', n.getAttribute('data-tab') === tabName);
  });
  render();
};

window.viewTaskDetail = function(taskId) {
  state.selectedTask = state.data.tasks.find(t => t.id === taskId);
  navigateToTab('detail');
};

window.triggerPlanProject = async function() {
  const promptInput = document.getElementById('run-prompt');
  const bpSelect = document.getElementById('run-blueprint');
  const autoSelect = document.getElementById('run-autonomy');
  const statusText = document.getElementById('run-status-text');

  const prompt = promptInput ? promptInput.value.trim() : '';
  const blueprint = bpSelect ? bpSelect.value : 'fastapi';
  const autonomy = autoSelect ? autoSelect.value : 'guarded';

  if (!prompt) {
    alert('Please enter a project prompt description.');
    return;
  }

  if (statusText) statusText.textContent = '⏳ Planning project (G1 → G2 → G3)...';
  showToast('Planning project: G1 Discovery → G2 Architecture → G3 Decomposition...');

  try {
    const res = await fetch('/api/run/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, blueprint, autonomy }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✓ Project planned! ${data.tasks_count} tasks and ${data.adrs_count} ADRs created.`);
      if (statusText) statusText.textContent = `✓ Planned: ${data.tasks_count} tasks ready`;
      await fetchData();
    } else {
      alert('Plan failed: ' + (data.error || 'Unknown error'));
      if (statusText) statusText.textContent = '❌ Plan failed';
    }
  } catch (err) {
    alert('Failed to plan project: ' + err);
    if (statusText) statusText.textContent = '❌ Error';
  }
};

window.triggerStartRun = async function() {
  const statusText = document.getElementById('run-status-text');
  if (statusText) statusText.textContent = '⏳ Starting autonomous orchestrator loop...';
  showToast('Starting autonomous orchestrator execution...');

  try {
    const res = await fetch('/api/run/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (data.success) {
      showToast('▶ Autonomous run loop started! Watch events and tasks update.');
      if (statusText) statusText.textContent = '▶ Orchestrator loop running';
      await fetchData();
    } else {
      alert('Start run failed: ' + (data.error || 'No tasks found. Plan project first.'));
      if (statusText) statusText.textContent = '❌ Start failed';
    }
  } catch (err) {
    alert('Failed to start run: ' + err);
  }
};

window.simulateApprovalRequest = async function() {
  showToast('Simulating high-risk task requiring human approval...');
  try {
    const res = await fetch('/api/approvals/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✓ Created high-risk task ${data.task_id}. Navigating to Approvals tab.`);
      await fetchData();
      navigateToTab('approvals');
    }
  } catch (err) {
    alert('Failed to simulate approval: ' + err);
  }
};

window.submitApproval = async function(taskId, action) {
  const steerInput = document.getElementById(`steer-${taskId}`);
  const feedback = steerInput ? steerInput.value.trim() : '';

  try {
    const res = await fetch(`/api/approvals/${taskId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, feedback }),
    });
    if (res.ok) {
      showToast(`✓ Action '${action}' successfully submitted for ${taskId}`);
      await fetchData();
    }
  } catch (err) {
    alert('Failed to submit approval: ' + err);
  }
};

window.updateTaskStatus = async function(taskId, newStatus) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    if (res.ok) {
      showToast(`✓ Task ${taskId} status updated to ${newStatus}`);
      await fetchData();
    }
  } catch (err) {
    alert('Failed to update task status: ' + err);
  }
};

window.injectTaskDirective = async function(taskId) {
  const input = document.getElementById('task-directive-input');
  const directive = input ? input.value.trim() : '';
  if (!directive) {
    alert('Please enter a directive message.');
    return;
  }

  try {
    const res = await fetch(`/api/tasks/${taskId}/directive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directive }),
    });
    if (res.ok) {
      showToast(`✓ Directive saved to task ${taskId}`);
      input.value = '';
      await fetchData();
    }
  } catch (err) {
    alert('Failed to inject directive: ' + err);
  }
};

window.toggleTaskApproval = async function(taskId, reqApproval) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle_approval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ human_approval: reqApproval }),
    });
    if (res.ok) {
      showToast(`✓ Task ${taskId} human_approval set to ${reqApproval}`);
      await fetchData();
    }
  } catch (err) {
    alert('Failed to toggle approval: ' + err);
  }
};

window.scanRetro = async function() {
  showToast('Scanning event store for failure patterns...');
  try {
    const res = await fetch('/api/retro/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✓ Retro scan complete: ${data.recommendations?.length || 0} patterns found.`);
      await fetchData();
    }
  } catch (err) {
    alert('Failed to scan retro: ' + err);
  }
};

window.applyRetro = async function(recId) {
  try {
    const res = await fetch('/api/retro/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: recId }),
    });
    if (res.ok) {
      showToast(`✓ Applied recommendation ${recId}`);
      await fetchData();
    }
  } catch (err) {
    alert('Failed to apply retro: ' + err);
  }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setupNavigation();
  fetchData();
  setInterval(() => {
    if (!document.hidden) {
      fetchData();
    }
  }, 3500); // 3.5s visibility-aware polling
});
