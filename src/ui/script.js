/* ═══════════════════════════════════════════════
   CONFIG — edit BASE_URL to point at your backend
═══════════════════════════════════════════════ */
let CONFIG = {
  BASE_URL: localStorage.getItem('ft_base_url') || '',   // e.g. https://abc123.execute-api.ap-south-1.amazonaws.com/prod
  API_KEY:  localStorage.getItem('ft_api_key')  || '',   // optional API Gateway key
  USER_ID:  localStorage.getItem('ft_user_id')  || 'TkM'
};

/* ═══════════════════════════════════
   LOCAL STATE (mirrors DynamoDB data)
═══════════════════════════════════ */
let entries = [];   // [{entryId, userId, vehicle, date, tripKm, fuel, cost, economy}]

/* ═══════════════════════════════════
   API STUBS — replace bodies with real fetch
═══════════════════════════════════ */

/**
 * STUB: POST /entries
 * Creates a new refueling entry in DynamoDB.
 * Replace the body of this function with the real API call.
 *
 * Expected request body:
 *   { userId, vehicle, date, tripKm, fuel, cost, economy }
 * Expected response:
 *   { entryId: "<uuid>", ...fields }
 */
async function apiCreateEntry(payload) {
  if (!CONFIG.BASE_URL) {
    // ── OFFLINE MODE: simulate a successful response locally ──
    return { ...payload, entryId: 'local-' + Date.now() };
  }

  // ── ONLINE MODE ──────────────────────────────────────────
  const res = await fetch(`${CONFIG.BASE_URL}/entries`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Create failed: ${res.status}`);
  return res.json();
}

/**
 * STUB: GET /entries?userId=&vehicle=&month=
 * Fetches all entries for a user, with optional filters.
 * Expected response:
 *   { items: [...] }
 */
async function apiFetchEntries({ vehicle = '', month = '' } = {}) {
  if (!CONFIG.BASE_URL) {
    // ── OFFLINE MODE ──
    return { items: entries };
  }

  // ── ONLINE MODE ──────────────────────────────────────────
  const params = new URLSearchParams({ userId: CONFIG.USER_ID });
  if (vehicle) params.set('vehicle', vehicle);
  if (month)   params.set('month', month);

  const res = await fetch(`${CONFIG.BASE_URL}/entries?${params}`, {
    headers: buildHeaders()
  });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json();
}

/**
 * STUB: DELETE /entries/{entryId}
 * Deletes a single entry from DynamoDB.
 */
async function apiDeleteEntry(entryId) {
  if (!CONFIG.BASE_URL) {
    // ── OFFLINE MODE ──
    entries = entries.filter(e => e.entryId !== entryId);
    return { deleted: true };
  }

  // ── ONLINE MODE ──────────────────────────────────────────
  const res = await fetch(`${CONFIG.BASE_URL}/entries/${entryId}`, {
    method: 'DELETE',
    headers: buildHeaders()
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
  return res.json();
}

/**
 * STUB: GET /health
 * Simple health-check probe to test connectivity.
 */
async function apiHealthCheck() {
  if (!CONFIG.BASE_URL) throw new Error('No BASE_URL configured');
  const res = await fetch(`${CONFIG.BASE_URL}/health`, { headers: buildHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ─── helper: build common request headers ─── */
function buildHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (CONFIG.API_KEY) h['x-api-key'] = CONFIG.API_KEY;
  return h;
}

/* ═══════════════════════════════════
   HANDLERS
═══════════════════════════════════ */
async function handleAddEntry() {
  const vehicle = document.getElementById('vehicle').value;
  const date    = document.getElementById('date').value;
  const tripKm  = parseFloat(document.getElementById('tripKm').value);
  const fuel    = parseFloat(document.getElementById('fuel').value);
  const cost    = parseFloat(document.getElementById('cost').value);

  if (!date || isNaN(tripKm) || isNaN(fuel) || isNaN(cost)) {
    showToast('Please fill all fields.', 'error'); return;
  }
  if (fuel <= 0 || tripKm < 0) {
    showToast('Fuel must be > 0 and Trip Km ≥ 0.', 'error'); return;
  }

  const economy = +(tripKm / fuel).toFixed(2);
  const payload = { userId: CONFIG.USER_ID, vehicle, date, tripKm, fuel, cost, economy };

  setLoading(true);
  try {
    const created = await apiCreateEntry(payload);
    entries.unshift(created);           // prepend to local state
    renderTable(entries);
    updateStats(entries);
    resetForm();
    showToast(`Entry added ✓  Economy: ${economy} km/L`, 'success');
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    setLoading(false);
  }
}

async function loadEntries() {
  setApiStatus('loading', 'Loading…');
  try {
    const data = await apiFetchEntries();
    entries = data.items || [];
    renderTable(entries);
    updateStats(entries);
    setApiStatus('ok', CONFIG.BASE_URL ? 'Connected to backend' : 'Running offline (local state)');
  } catch (err) {
    setApiStatus('err', 'Backend unreachable');
    showToast('Could not load entries: ' + err.message, 'error');
  }
}

async function applyFilters() {
  const vehicle = document.getElementById('filterVehicle').value;
  const month   = document.getElementById('filterMonth').value;

  try {
    const data = await apiFetchEntries({ vehicle, month });
    renderTable(data.items || []);
  } catch {
    // fallback: filter local state
    const filtered = entries.filter(e => {
      const vMatch = !vehicle || e.vehicle === vehicle;
      const mMatch = !month   || e.date.startsWith(month);
      return vMatch && mMatch;
    });
    renderTable(filtered);
  }
}

async function deleteEntry(entryId) {
  if (!confirm('Delete this entry?')) return;
  try {
    await apiDeleteEntry(entryId);
    entries = entries.filter(e => e.entryId !== entryId);
    renderTable(entries);
    updateStats(entries);
    showToast('Entry deleted.', 'success');
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

function handleLogout() {
  if (confirm('Log out?')) showToast('Logged out. (Implement auth redirect here.)', 'success');
}

/* ═══════════════════════════════════
   RENDER
═══════════════════════════════════ */
function renderTable(data) {
  const tbody = document.getElementById('historyBody');
  const empty = document.getElementById('emptyState');
  tbody.innerHTML = '';
  empty.style.display = data.length ? 'none' : 'block';

  data.forEach(e => {
    const eco = parseFloat(e.economy) || (e.fuel > 0 ? +(e.tripKm / e.fuel).toFixed(2) : 0);
    const ecoClass = eco >= 20 ? 'eco-good' : eco >= 12 ? 'eco-mid' : 'eco-low';
    const badgeClass = e.vehicle === 'Two-Wheeler' ? 'badge-two' : 'badge-four';

    tbody.insertAdjacentHTML('beforeend', `
      <tr>
        <td>${formatDate(e.date)}</td>
        <td><span class="badge ${badgeClass}">${e.vehicle}</span></td>
        <td>${(+e.tripKm).toLocaleString()} km</td>
        <td>${(+e.fuel).toFixed(1)} L</td>
        <td>₹${(+e.cost).toLocaleString()}</td>
        <td><span class="economy-pill ${ecoClass}">${eco} km/L</span></td>
        <td><button class="btn-delete" onclick="deleteEntry('${e.entryId}')" title="Delete">✕</button></td>
      </tr>
    `);
  });
}

function updateStats(data) {
  const totalFuel = data.reduce((s, e) => s + (+e.fuel || 0), 0);
  const totalCost = data.reduce((s, e) => s + (+e.cost || 0), 0);
  const avgEco    = data.length
    ? (data.reduce((s, e) => s + (+e.economy || 0), 0) / data.length).toFixed(1)
    : '—';

  document.getElementById('stat-entries').textContent = data.length;
  document.getElementById('stat-fuel').textContent    = totalFuel.toFixed(1);
  document.getElementById('stat-cost').textContent    = '₹' + totalCost.toLocaleString('en-IN');
  document.getElementById('stat-econ').textContent    = avgEco + (data.length ? ' km/L' : '');
}

/* ═══════════════════════════════════
   CONFIG MODAL
═══════════════════════════════════ */
function openConfig() {
  document.getElementById('cfgBaseUrl').value = CONFIG.BASE_URL;
  document.getElementById('cfgApiKey').value  = CONFIG.API_KEY;
  document.getElementById('cfgUserId').value  = CONFIG.USER_ID;
  document.getElementById('configModal').classList.add('open');
}
function closeConfig() {
  document.getElementById('configModal').classList.remove('open');
}
async function saveConfig() {
  CONFIG.BASE_URL = document.getElementById('cfgBaseUrl').value.trim().replace(/\/$/, '');
  CONFIG.API_KEY  = document.getElementById('cfgApiKey').value.trim();
  CONFIG.USER_ID  = document.getElementById('cfgUserId').value.trim() || 'TkM';
  localStorage.setItem('ft_base_url', CONFIG.BASE_URL);
  localStorage.setItem('ft_api_key',  CONFIG.API_KEY);
  localStorage.setItem('ft_user_id',  CONFIG.USER_ID);

  if (CONFIG.BASE_URL) {
    setApiStatus('loading', 'Testing connection…');
    try {
      await apiHealthCheck();
      setApiStatus('ok', 'Connected to backend');
      showToast('Backend connected ✓', 'success');
      loadEntries();
    } catch (err) {
      setApiStatus('err', 'Connection failed');
      showToast('Health check failed: ' + err.message, 'error');
    }
  }
  closeConfig();
}

/* ═══════════════════════════════════
   UTILS
═══════════════════════════════════ */
function setLoading(v) {
  const btn = document.getElementById('addBtn');
  btn.classList.toggle('loading', v);
  btn.disabled = v;
}
function setApiStatus(type, msg) {
  const el = document.getElementById('apiStatus');
  el.className = 'api-status ' + type;
  document.getElementById('apiStatusText').textContent = msg;
}
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = (type === 'success' ? '✓ ' : '✕ ') + msg;
  t.className = 'show ' + type;
  setTimeout(() => { t.className = ''; }, 3500);
}
function resetForm() {
  ['date','tripKm','fuel','cost'].forEach(id => document.getElementById(id).value = '');
}
function formatDate(d) {
  if (!d) return '—';
  const [y,m,day] = d.split('-');
  return `${day}/${m}/${y}`;
}
function exportCSV() {
  if (!entries.length) { showToast('No data to export.', 'error'); return; }
  const rows = [['Date','Vehicle','Trip Km','Fuel (L)','Cost (₹)','Economy (km/L)']];
  entries.forEach(e => rows.push([e.date, e.vehicle, e.tripKm, e.fuel, e.cost, e.economy]));
  const csv = rows.map(r => r.join(',')).join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = 'fueltrack_export.csv';
  a.click();
}

/* ═══════════════════════════════════
   INIT
═══════════════════════════════════ */
document.getElementById('date').valueAsDate = new Date();
loadEntries();