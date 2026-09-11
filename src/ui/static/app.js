/**
 * Prompt2Product Dashboard SPA Logic (docs/12 §2.A, docs/08 Faz 10)
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
};

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
async function fetchData() {
  try {
    const [stateRes, tasksRes, eventsRes, approvalsRes, connsRes, retroRes] = await Promise.all([
      fetch('/api/state').then(r => r.json()),
      fetch('/api/tasks').then(r => r.json()),
      fetch('/api/events').then(r => r.json()),
      fetch('/api/approvals').then(r => r.json()),
      fetch('/api/connections').then(r => r.json()),
      fetch('/api/retro').then(r => r.json()),
    ]);

    state.data.state = stateRes.state;
    state.data.tasks = tasksRes.tasks || [];
    state.data.events = eventsRes.events || [];
    state.data.approvals = approvalsRes.approvals || [];
    state.data.connections = connsRes.connections || [];
    state.data.retro = retroRes.recommendations || [];

    render();
  } catch (err) {
    console.error('Failed to fetch dashboard data:', err);
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
  const completed = tasks.filter(t => t.status === 'COMPLETED').length;
  const inProgress = tasks.filter(t => t.status === 'RUNNING' || t.status === 'IMPLEMENTING').length;
  const blocked = tasks.filter(t => t.status === 'BLOCKED' || t.status === 'ESCALATED').length;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Run Overview</h1>
        <p class="page-subtitle">Autonomous execution state and decision lineage</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <span class="badge badge-success">${completed} Completed</span>
        <span class="badge badge-running">${inProgress} Running</span>
        ${blocked > 0 ? `<span class="badge badge-danger">${blocked} Blocked</span>` : ''}
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Planning Chain Gates</h2>
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

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Governance & Autonomous Decisions</h2>
        <span style="font-size: 12px; color: var(--text-secondary);">Decisions made in user's absence</span>
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
          ${decisions.length === 0 ? '<tr><td colspan="5" style="color: var(--text-tertiary);">No decisions recorded yet.</td></tr>' : ''}
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
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Execution Waves</h2>
        <span style="font-size: 12px; color: var(--text-tertiary);">Shape encodes risk: rounded = low, rect = med, notched = high</span>
      </div>

      ${waves.length === 0 ? `
        <div class="wave-band">
          <div class="wave-title">WAVE 1 (INITIAL PARALLEL BATCH)</div>
          <div class="wave-tasks">
            ${allTasks.map(t => `
              <div class="task-node risk-${t.risk || 'low'}" onclick="viewTaskDetail('${t.id}')">
                <span class="tabular"><strong>${t.id}</strong></span>
                <span>${t.title}</span>
                <span class="badge badge-${t.status === 'COMPLETED' ? 'success' : 'running'}">${t.status || 'PENDING'}</span>
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
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderTaskDetail() {
  const task = state.selectedTask || state.data.tasks[0];
  if (!task) {
    return `<div class="panel"><p style="color: var(--text-tertiary);">No task selected.</p></div>`;
  }

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Task Detail: ${task.id}</h1>
        <p class="page-subtitle">${task.title}</p>
      </div>
      <div>
        <span class="badge badge-${task.risk === 'high' ? 'danger' : 'running'}">Risk: ${task.risk}</span>
        <span class="badge badge-success">${task.status || 'PENDING'}</span>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Contract Specification</h2>
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
  const approvals = state.data.approvals;

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Human Approvals</h1>
        <p class="page-subtitle">Decisions requiring human intervention (Gate G, High Risk, or Escalations)</p>
      </div>
    </div>

    ${approvals.length === 0 ? `
      <div class="panel">
        <p style="color: var(--status-success); font-weight: 500;">✓ No pending human approvals. Autonomous loop is running unimpeded.</p>
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
        </div>

        <div style="display: flex; gap: 12px; align-items: center; margin-top: 16px;">
          <button class="btn btn-brand" onclick="submitApproval('${app.id}', 'approve')">Approve Task</button>
          <button class="btn btn-danger" onclick="submitApproval('${app.id}', 'reject')">Reject</button>
          <input type="text" id="steer-${app.id}" placeholder="Provide steer feedback..." style="flex: 1; padding: 8px 12px; background: var(--bg-inset); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; font-size: 13px;">
          <button class="btn btn-secondary" onclick="submitApproval('${app.id}', 'steer')">Steer</button>
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
    </div>

    <div class="panel">
      ${recs.length === 0 ? `
        <p style="color: var(--status-success);">✓ Clean run history: No recurring failure patterns detected.</p>
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

// --- User Actions ---
window.viewTaskDetail = function(taskId) {
  state.selectedTask = state.data.tasks.find(t => t.id === taskId);
  state.currentTab = 'detail';
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(n => {
    n.classList.toggle('active', n.getAttribute('data-tab') === 'detail');
  });
  render();
};

window.submitApproval = async function(taskId, action) {
  const steerInput = document.getElementById(`steer-${taskId}`);
  const feedback = steerInput ? steerInput.value : '';

  try {
    const res = await fetch(`/api/approvals/${taskId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, feedback }),
    });
    if (res.ok) {
      await fetchData();
    }
  } catch (err) {
    alert('Failed to submit approval: ' + err);
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
      alert(`Applied recommendation ${recId}`);
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
  setInterval(fetchData, 3000); // 3s polling for reactive dashboard
});
