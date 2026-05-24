let refreshCountdown = 15;

// Toast
function showToast(msg, duration = 3500) {

  const t = document.getElementById('toast');

  t.textContent = msg;

  t.classList.add('show');

  setTimeout(() => {
    t.classList.remove('show');
  }, duration);
}

// Ping
function pingServer(id, name) {

  showToast(`Pinging ${name}...`);

  fetch(`/api/ping/${id}`, {
    method:'POST'
  })

  .then(r => r.json())

  .then(data => {

    const ms = data.ping_ms
      ? `${data.ping_ms}ms`
      : 'timeout';

    showToast(
      `${name}: ${data.status.toUpperCase()} — ${ms}`
    );

    refreshNow();
  })

  .catch(() => {
    showToast('Ping request failed');
  });
}

// Restart
function restartServer(id, name) {

  if (!confirm(`Restart ${name}?`)) return;

  showToast(`Restarting ${name}...`, 5000);

  fetch(`/api/restart/${id}`, {
    method:'POST'
  })

  .then(r => r.json())

  .then(data => {

    showToast(
      data.success
      ? `✓ ${name}: ${data.message}`
      : `✗ ${name}: ${data.message}`,
      5000
    );
  })

  .catch(() => {
    showToast('Restart failed');
  });
}

// Filter
function filterServers(q) {

  q = q.toLowerCase();

  document.querySelectorAll('.server-row')
  .forEach(row => {

    const name = row.dataset.name || '';
    const ip   = row.dataset.ip || '';

    row.style.display =
      (name.includes(q) || ip.includes(q))
      ? ''
      : 'none';
  });
}

// Graph View
function showGraphView() {

  document.getElementById('graph-section')
  .style.display = 'block';

  document.getElementById('server-section')
  .style.display = 'none';

  document.getElementById('graph-btn')
  .classList.add('active');

  document.getElementById('server-btn')
  .classList.remove('active');
}

// Server View
function showServerView() {

  document.getElementById('graph-section')
  .style.display = 'none';

  document.getElementById('server-section')
  .style.display = 'block';

  document.getElementById('server-btn')
  .classList.add('active');

  document.getElementById('graph-btn')
  .classList.remove('active');
}

// Refresh
function refreshNow() {

  const btn  = document.getElementById('refresh-btn');
  const icon = document.getElementById('refresh-icon');

  btn.disabled = true;

  icon.classList.add('spin');

  fetch('/api/status')

  .then(r => r.json())

  .then(data => {

    document.getElementById('stat-total')
    .textContent = data.stats.total;

    document.getElementById('stat-up')
    .textContent = data.stats.up;

    document.getElementById('stat-down')
    .textContent = data.stats.down;

    document.getElementById('stat-warn')
    .textContent = data.stats.warning;

    document.getElementById('stat-alerts')
    .textContent = data.stats.alerts;

    data.servers.forEach(srv => {

      const row = document.querySelector(
        `.server-row[data-id="${srv.id}"]`
      );

      if (!row) return;

      const dot = row.querySelector('.status-dot');

      const label = row.querySelector('.status-label');

      const status = srv.status || 'unknown';

      dot.className =
        `status-dot status-${status}`;

      label.textContent =
        status.toUpperCase();
    });

    if (typeof drawTopology === 'function') {
      drawTopology(data.servers);
    }

    const t = new Date();

    document.getElementById('last-refresh')
    .textContent = t.toLocaleTimeString();

    refreshCountdown = 15;
  })

  .catch(err => {
    console.warn(err);
  })

  .finally(() => {

    btn.disabled = false;

    icon.classList.remove('spin');
  });
}

// Countdown
function updateCountdown() {

  const el = document.getElementById(
    'refresh-countdown'
  );

  if (!el) return;

  el.textContent = refreshCountdown;

  refreshCountdown--;

  if (refreshCountdown < 0) {
    refreshCountdown = 15;
  }
}
function showHistory(id, name) {

  let modal = document.getElementById('history-modal');

  // create modal dynamically
  if (!modal) {

    modal = document.createElement('div');

    modal.id = 'history-modal';

    modal.className = 'history-modal';

    modal.innerHTML = `

      <div class="history-box">

        <div class="history-top">

          <h3 id="history-title">
            Server History
          </h3>

          <button
          class="history-close"
          onclick="closeHistory()">

            ✕
          </button>

        </div>

        <div id="history-content"
        class="history-content">

          Loading...

        </div>

      </div>
    `;

    document.body.appendChild(modal);
  }

  document.getElementById(
    'history-title'
  ).textContent = `History — ${name}`;

  document.getElementById(
    'history-content'
  ).innerHTML =
    '<div class="history-loading">Loading...</div>';

  modal.style.display = 'flex';

  fetch(`/api/history/${id}`)

  .then(r => r.json())

  .then(rows => {

    if (!rows.length) {

      document.getElementById(
        'history-content'
      ).innerHTML = `

        <div class="history-empty">

          No history available

        </div>
      `;

      return;
    }

    document.getElementById(
      'history-content'
    ).innerHTML = rows.map(r => {

      const cls =
        r.status === 'up'
        ? 'hist-up'
        : r.status === 'down'
        ? 'hist-down'
        : 'hist-warning';

      return `

        <div class="history-row">

          <div class="history-status ${cls}">
            ${r.status.toUpperCase()}
          </div>

          <div class="history-ms">

            ${
              r.ping_ms
              ? r.ping_ms + 'ms'
              : 'timeout'
            }

          </div>

          <div class="history-time">

            ${r.checked_at}

          </div>

        </div>
      `;

    }).join('');
  })

  .catch(() => {

    document.getElementById(
      'history-content'
    ).innerHTML = `

      <div class="history-empty">

        Failed to load history

      </div>
    `;
  });
}

function closeHistory() {

  const modal = document.getElementById(
    'history-modal'
  );

  if (modal) {
    modal.style.display = 'none';
  }
}
function deleteSingleServer(id, name) {

  if (!confirm(`Delete ${name}?`)) return;

  fetch('/api/delete-server/' + id, {
    method:'POST'
  })

  .then(r => r.json())

  .then(data => {

    showToast(data.message);

    const row = document.querySelector(
      `.server-row[data-id="${id}"]`
    );

    if (row) {
      row.remove();
    }
  })

  .catch(() => {
    showToast('Delete failed');
  });
}



setInterval(updateCountdown, 1000);

setInterval(refreshNow, 15000);

refreshNow();