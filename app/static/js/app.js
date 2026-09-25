/**
 * PhishGuard v2 — Dashboard Application (Vanilla JS SPA)
 *
 * Features: Auth, Campaigns, URL Analyzer, Email Settings,
 *           Notifications, Audit Logs, SSE Live Feed, Analytics
 */

// ── State ────────────────────────────────────────────────────────────
const state = {
    token: localStorage.getItem('pg_token') || null,
    username: localStorage.getItem('pg_username') || null,
    currentSection: 'dashboard',
    sseSource: null,
};

// ── API Client ───────────────────────────────────────────────────────
const api = {
    async request(method, url, data = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
        const opts = { method, headers };
        if (data) opts.body = JSON.stringify(data);
        const resp = await fetch(url, opts);
        if (resp.status === 401) { logout(); throw new Error('Session expired'); }
        if (resp.status === 204) return null;
        const json = await resp.json();
        if (!resp.ok) throw new Error(json.detail || 'API error');
        return json;
    },
    get: (u) => api.request('GET', u),
    post: (u, d) => api.request('POST', u, d),
    delete: (u) => api.request('DELETE', u),
    patch: (u, d) => api.request('PATCH', u, d),
};

// ── Toasts ───────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity='0'; t.style.transform='translateX(100%)'; setTimeout(()=>t.remove(),300); }, 3500);
}

// ── Auth ─────────────────────────────────────────────────────────────
function saveAuth(token, username) {
    state.token = token; state.username = username;
    localStorage.setItem('pg_token', token);
    localStorage.setItem('pg_username', username);
}
function logout() {
    state.token = null; state.username = null;
    localStorage.removeItem('pg_token'); localStorage.removeItem('pg_username');
    if (state.sseSource) { state.sseSource.close(); state.sseSource = null; }
    renderApp();
}
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    errEl.textContent = '';
    try {
        const st = await api.get('/api/auth/status');
        const ep = st.setup_required ? '/api/auth/register' : '/api/auth/login';
        const r = await api.post(ep, { username, password });
        saveAuth(r.access_token, r.username);
        showToast(`Welcome, ${r.username}!`, 'success');
        renderApp();
    } catch (err) { errEl.textContent = err.message; }
}

// ── Navigation ───────────────────────────────────────────────────────
function navigate(section) {
    state.currentSection = section;
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const el = document.getElementById(`section-${section}`);
    if (el) el.classList.add('active');
    const nav = document.querySelector(`[data-nav="${section}"]`);
    if (nav) nav.classList.add('active');
    loadSectionData(section);
}
async function loadSectionData(section) {
    try {
        switch(section) {
            case 'dashboard': await loadDashboard(); break;
            case 'campaigns': await loadCampaigns(); break;
            case 'scan-history': await loadScanHistory(); break;
            case 'email-settings': await loadEmailConfig(); break;
            case 'notification-logs': await loadNotificationLogs(); break;
            case 'audit-logs': await loadAuditLogs(); break;
        }
    } catch(err) { console.error(err); }
}

// ── Dashboard ────────────────────────────────────────────────────────
async function loadDashboard() {
    const d = await api.get('/api/analytics/overview');
    document.getElementById('stat-campaigns').textContent = d.total_campaigns;
    document.getElementById('stat-active').textContent = d.active_campaigns;
    document.getElementById('stat-targets').textContent = d.total_targets;
    document.getElementById('stat-clicked').textContent = d.total_clicked;
    document.getElementById('stat-click-rate').textContent = d.click_rate + '%';
    document.getElementById('stat-url-scans').textContent = d.total_url_scans;
    document.getElementById('stat-events').textContent = d.total_events;
    document.getElementById('stat-submitted').textContent = d.total_submitted;
}

// ── SSE Live Feed ────────────────────────────────────────────────────
function connectSSE() {
    if (!state.token) return;
    if (state.sseSource) state.sseSource.close();

    const url = `/api/sse/events?token=${state.token}`;
    // SSE with auth: we use a custom EventSource approach via fetch
    const evtSource = new EventSource(url);
    state.sseSource = evtSource;

    const statusEl = document.getElementById('sse-status');

    evtSource.onopen = () => {
        if (statusEl) { statusEl.textContent = 'Connected'; statusEl.className = 'badge badge-active'; }
    };
    evtSource.onerror = () => {
        if (statusEl) { statusEl.textContent = 'Reconnecting…'; statusEl.className = 'badge badge-paused'; }
    };
    evtSource.addEventListener('campaign_event', (e) => {
        try {
            const data = JSON.parse(e.data);
            addLiveFeedItem(data);
            // Refresh dashboard stats
            if (state.currentSection === 'dashboard') loadDashboard();
        } catch(err) { console.error('SSE parse error', err); }
    });
    evtSource.addEventListener('event', (e) => {
        try {
            const data = JSON.parse(e.data);
            if (data.type === 'campaign_event') addLiveFeedItem(data);
        } catch(err) {}
    });
}

function addLiveFeedItem(data) {
    const feed = document.getElementById('live-feed');
    const emptyEl = document.getElementById('live-feed-empty');
    if (emptyEl) emptyEl.remove();

    const time = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : 'now';
    const item = document.createElement('div');
    item.className = 'check-item';
    item.style.animation = 'fadeIn 0.3s ease-out';
    item.innerHTML = `
        <span class="check-status">${data.event_type === 'click' ? '🖱️' : data.event_type === 'submit' ? '📝' : '📡'}</span>
        <span class="check-name" style="min-width:100px;color:var(--accent-cyan)">${time}</span>
        <span class="check-name">${escHtml(data.session_id || '')}</span>
        <span class="check-detail">
            ${escHtml(data.event_type || '')}
            ${data.browser ? ' · ' + escHtml(data.browser) : ''}
            ${data.campaign_name ? ' · <em>' + escHtml(data.campaign_name) + '</em>' : ''}
        </span>
    `;
    feed.insertBefore(item, feed.firstChild);

    // Keep max 50 items
    while (feed.children.length > 50) feed.removeChild(feed.lastChild);
}

// ── Campaigns ────────────────────────────────────────────────────────
async function loadCampaigns() {
    const campaigns = await api.get('/api/campaigns');
    const tbody = document.getElementById('campaigns-table-body');
    if (!campaigns.length) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:40px;color:var(--text-muted)">No campaigns yet. Create your first one! 🚀</td></tr>`;
        return;
    }
    tbody.innerHTML = campaigns.map(c => `<tr>
        <td><strong style="color:var(--text-primary)">${escHtml(c.name)}</strong></td>
        <td><span class="badge badge-${c.status}">${c.status}</span></td>
        <td>${c.total_targets}</td>
        <td>${c.clicked}</td>
        <td>${c.click_rate}%</td>
        <td>${c.notifications_enabled ? '✅ ' + escHtml(c.notification_email||'') : '<span style="color:var(--text-muted)">Off</span>'}</td>
        <td>${new Date(c.created_at).toLocaleDateString()}</td>
        <td>
            <button class="btn btn-sm btn-secondary" onclick="viewCampaign(${c.id})">View</button>
            <button class="btn btn-sm btn-secondary" onclick="viewAnalytics(${c.id})">📊</button>
            <button class="btn btn-sm btn-danger" onclick="deleteCampaign(${c.id})">🗑️</button>
        </td>
    </tr>`).join('');
}

async function createCampaign(e) {
    e.preventDefault();
    try {
        await api.post('/api/campaigns', {
            name: document.getElementById('campaign-name').value,
            description: document.getElementById('campaign-desc').value,
            campaign_type: document.getElementById('campaign-type').value,
            expires_in_hours: parseInt(document.getElementById('campaign-expiry').value) || 72,
            notification_email: document.getElementById('campaign-notif-email').value,
            notification_frequency: document.getElementById('campaign-notif-freq').value,
            notifications_enabled: document.getElementById('campaign-notif-enabled').checked,
            authorized_simulation: document.getElementById('campaign-authorized').checked,
            redirect_url: document.getElementById('campaign-redirect-url') ? document.getElementById('campaign-redirect-url').value.trim() : "",
        });
        showToast('Campaign created!', 'success');
        closeModal('campaign-modal');
        document.getElementById('create-campaign-form').reset();
        await loadCampaigns();
        await loadDashboard();
    } catch(err) { showToast(err.message, 'error'); }
}

async function deleteCampaign(id) {
    if (!confirm('Delete this campaign and all its data?')) return;
    try {
        await api.delete(`/api/campaigns/${id}`);
        showToast('Campaign deleted', 'success');
        await loadCampaigns(); await loadDashboard();
    } catch(err) { showToast(err.message, 'error'); }
}

async function viewCampaign(id) {
    try {
        const c = await api.get(`/api/campaigns/${id}`);
        const body = document.getElementById('detail-modal-body');
        let targetsHtml = '';
        if (c.targets.length > 0) {
            targetsHtml = `<div class="table-container" style="margin-top:16px"><table>
                <thead><tr><th>Name</th><th>Email</th><th>Clicked</th><th>Link</th><th>QR</th></tr></thead>
                <tbody>${c.targets.map(t => `<tr>
                    <td>${escHtml(t.name)}</td>
                    <td>${escHtml(t.email)}</td>
                    <td>${t.clicked ? '✅' : '❌'}</td>
                    <td><div class="link-box"><span style="flex:1">${escHtml(t.link)}</span>
                        <button class="copy-btn" onclick="copyText('${t.link}')">📋</button></div></td>
                    <td><button class="btn btn-sm btn-secondary" onclick="showQR(${c.id},${t.id})">QR</button></td>
                </tr>`).join('')}</tbody></table></div>`;
        } else {
            targetsHtml = `<div class="empty-state" style="padding:30px"><p>No targets added yet</p></div>`;
        }
        body.innerHTML = `
            <div style="margin-bottom:20px">
                <h3 style="color:var(--text-primary)">${escHtml(c.name)}</h3>
                <p style="color:var(--text-secondary);font-size:13px">${escHtml(c.description)}</p>
                <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
                    <span class="badge badge-${c.status}">${c.status}</span>
                    <span class="badge" style="background:var(--bg-card);border:1px solid var(--border);color:var(--text-secondary)">${c.targets.length} targets</span>
                    <span class="badge" style="background:var(--bg-card);border:1px solid var(--border);color:var(--text-secondary)">${c.event_count} events</span>
                    ${c.notifications_enabled ? '<span class="badge badge-active">📧 Notifications ON</span>' : ''}
                    ${c.authorized_simulation ? '<span class="badge badge-active">✅ Authorized</span>' : ''}
                </div>
            </div>
            <div class="card" style="margin-bottom:16px;padding:16px">
                <h4 style="margin-bottom:12px;font-size:14px">➕ Add Target</h4>
                <form onsubmit="addTarget(event,${c.id})" style="display:flex;gap:8px;flex-wrap:wrap">
                    <input type="text" id="target-name" placeholder="Name" class="form-input" style="flex:1;min-width:120px">
                    <input type="text" id="target-email" placeholder="Email" class="form-input" style="flex:1;min-width:120px">
                    <button type="submit" class="btn btn-primary btn-sm">Add</button>
                </form>
            </div>
            ${targetsHtml}`;
        openModal('detail-modal');
    } catch(err) { showToast(err.message, 'error'); }
}

async function addTarget(e, cid) {
    e.preventDefault();
    try {
        await api.post(`/api/campaigns/${cid}/targets`, {
            targets: [{ name: document.getElementById('target-name').value, email: document.getElementById('target-email').value }],
        });
        showToast('Target added!', 'success');
        await viewCampaign(cid);
    } catch(err) { showToast(err.message, 'error'); }
}

async function showQR(cid, tid) {
    try {
        const d = await api.get(`/api/campaigns/${cid}/targets/${tid}/qr`);
        document.getElementById('detail-modal-body').innerHTML = `
            <div class="qr-display">
                <h3>📱 QR Code</h3>
                <img src="${d.qr_code}" alt="QR Code" />
                <div class="link-box" style="max-width:400px">
                    <span style="flex:1">${escHtml(d.link)}</span>
                    <button class="copy-btn" onclick="copyText('${d.link}')">📋</button>
                </div>
                <button class="btn btn-secondary" onclick="viewCampaign(${cid})">← Back</button>
            </div>`;
    } catch(err) { showToast(err.message, 'error'); }
}

// ── Analytics ────────────────────────────────────────────────────────
async function viewAnalytics(cid) {
    try {
        const d = await api.get(`/api/analytics/campaign/${cid}`);
        navigate('campaign-analytics');
        const section = document.getElementById('section-campaign-analytics');
        section.classList.add('active');
        section.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">📊 ${escHtml(d.campaign_name)}</h1>
                <p class="page-subtitle">Campaign Analytics & Insights</p>
            </div>
            <div class="stats-grid">
                <div class="stat-card purple"><div class="stat-icon">🎯</div><div class="stat-value">${d.total_targets}</div><div class="stat-label">Total Targets</div></div>
                <div class="stat-card cyan"><div class="stat-icon">🖱️</div><div class="stat-value">${d.clicked}</div><div class="stat-label">Clicked (${d.click_rate}%)</div></div>
                <div class="stat-card green"><div class="stat-icon">📝</div><div class="stat-value">${d.submitted}</div><div class="stat-label">Completed (${d.submit_rate}%)</div></div>
                <div class="stat-card amber"><div class="stat-icon">📡</div><div class="stat-value">${d.total_events}</div><div class="stat-label">Total Events</div></div>
            </div>
            <div class="grid-2">
                <div class="card"><div class="card-header"><span class="card-title">📈 Event Timeline</span></div><div class="chart-container"><canvas id="timeline-chart"></canvas></div></div>
                <div class="card"><div class="card-header"><span class="card-title">📊 Event Types</span></div><div class="chart-container"><canvas id="events-chart"></canvas></div></div>
            </div>
            ${d.locations.length ? `<div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">🗺️ Consent-Based Locations</span></div><div id="analytics-map" class="map-container"></div></div>` : ''}
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">📋 Recent Events</span></div>
                <div class="table-container"><table>
                    <thead><tr><th>Type</th><th>Session</th><th>Browser</th><th>IP</th><th>Consent</th><th>Time</th></tr></thead>
                    <tbody>${d.recent_events.map(e => `<tr>
                        <td><span class="badge badge-active">${e.event_type}</span></td>
                        <td style="font-family:monospace;color:var(--accent-cyan)">${e.session_id || ''}</td>
                        <td>${e.browser_family || ''}</td>
                        <td style="font-family:monospace">${e.ip_address}</td>
                        <td>${e.location_consent ? '✅' : '❌'}</td>
                        <td>${new Date(e.timestamp).toLocaleString()}</td>
                    </tr>`).join('')}</tbody>
                </table></div>
            </div>
            <div style="margin-top:16px"><button class="btn btn-secondary" onclick="navigate('campaigns')">← Back to Campaigns</button></div>`;
        renderTimelineChart(d.timeline);
        renderEventsChart(d.event_types);
        if (d.locations.length) renderMap(d.locations);
    } catch(err) { showToast(err.message, 'error'); }
}

function renderTimelineChart(timeline) {
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById('timeline-chart'); if (!ctx) return;
    const last24 = timeline.slice(-24);
    new Chart(ctx, {
        type:'line', data: {
            labels: last24.map((_,i) => `${24-i}h`),
            datasets: [{ label:'Events', data:last24.map(t=>t.count), borderColor:'#7c3aed', backgroundColor:'rgba(124,58,237,.1)', fill:true, tension:.4, pointRadius:2 }],
        }, options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b',maxTicksLimit:8}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#64748b'},beginAtZero:true}} }
    });
}
function renderEventsChart(types) {
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById('events-chart'); if (!ctx) return;
    const labels = Object.keys(types), values = Object.values(types);
    const colors = ['#7c3aed','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899'];
    new Chart(ctx, {
        type:'doughnut', data: { labels, datasets:[{data:values,backgroundColor:colors.slice(0,labels.length),borderWidth:0}] },
        options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'bottom',labels:{color:'#94a3b8',padding:16}}} }
    });
}
function renderMap(locations) {
    if (typeof L === 'undefined') return;
    const el = document.getElementById('analytics-map'); if (!el) return;
    const map = L.map(el).setView([locations[0].lat, locations[0].lng], 10);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution:'© OpenStreetMap' }).addTo(map);
    locations.forEach(loc => L.marker([loc.lat,loc.lng]).addTo(map).bindPopup(`<strong>${loc.event_type}</strong><br>${loc.timestamp}`));
}

// ── URL Analyzer ─────────────────────────────────────────────────────
async function analyzeURL(e) {
    e.preventDefault();
    const url = document.getElementById('url-input').value;
    const r = document.getElementById('url-results');
    r.innerHTML = '<div class="spinner"></div>';
    try {
        const d = await api.post('/api/url/analyze', { url });
        r.innerHTML = `
            <div class="card">
                <div class="risk-meter">
                    <div class="risk-score-display">
                        <div><div class="risk-score-number ${d.risk_level}">${d.risk_score}</div><div style="color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:1px">Risk Score / 100</div></div>
                        <span class="badge badge-${d.risk_level}" style="font-size:14px;padding:8px 16px">${d.risk_level.toUpperCase()}</span>
                    </div>
                    <div class="risk-bar-bg"><div class="risk-bar-fill ${d.risk_level}" style="width:${d.risk_score}%"></div></div>
                </div>
                <p style="color:var(--text-secondary);font-size:13px;margin-bottom:20px">${escHtml(d.summary)}</p>
                <div class="table-container"><ul class="check-list">
                    ${d.checks.map(c => `<li class="check-item"><span class="check-status">${c.status.split(' ')[0]}</span><span class="check-name">${escHtml(c.name)}</span><span class="check-detail">${escHtml(c.detail)}</span></li>`).join('')}
                </ul></div>
            </div>`;
        showToast('Scan complete!', 'success');
    } catch(err) { r.innerHTML = `<p style="color:var(--accent-red)">Error: ${escHtml(err.message)}</p>`; showToast(err.message, 'error'); }
}

// ── Scan History ─────────────────────────────────────────────────────
async function loadScanHistory() {
    const scans = await api.get('/api/url/history');
    const tb = document.getElementById('scan-history-body');
    if (!scans.length) { tb.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:40px;color:var(--text-muted)">No scans yet 🔍</td></tr>`; return; }
    tb.innerHTML = scans.map(s => `<tr>
        <td style="font-family:monospace;color:var(--accent-cyan);word-break:break-all">${escHtml(s.url)}</td>
        <td><span class="badge badge-${s.risk_level}">${s.risk_level}</span></td>
        <td><strong style="color:var(--text-primary)">${s.risk_score}/100</strong></td>
        <td>${new Date(s.scan_date).toLocaleString()}</td>
    </tr>`).join('');
}

// ── Email Settings ───────────────────────────────────────────────────
const smtpPresets = {
    gmail: { host: 'smtp.gmail.com', port: 587 },
    outlook: { host: 'smtp-mail.outlook.com', port: 587 },
    yahoo: { host: 'smtp.mail.yahoo.com', port: 587 },
    custom: { host: '', port: 587 },
};

function onProviderChange() {
    const p = document.getElementById('smtp-provider').value;
    const preset = smtpPresets[p];
    if (preset) {
        document.getElementById('smtp-host').value = preset.host;
        document.getElementById('smtp-port').value = preset.port;
    }
}

async function loadEmailConfig() {
    try {
        const d = await api.get('/api/email/config');
        const statusEl = document.getElementById('email-config-status');
        if (d.configured) {
            document.getElementById('smtp-provider').value = d.smtp_provider || 'custom';
            document.getElementById('smtp-host').value = d.smtp_host || '';
            document.getElementById('smtp-port').value = d.smtp_port || 587;
            document.getElementById('smtp-username').value = d.smtp_username || '';
            document.getElementById('sender-email').value = d.sender_email || '';
            document.getElementById('sender-name').value = d.sender_name || 'PhishGuard';
            document.getElementById('notify-click').checked = d.notify_on_click;
            document.getElementById('notify-submit').checked = d.notify_on_submit;
            document.getElementById('notify-location').checked = d.notify_on_location;
            document.getElementById('notify-daily').checked = d.notify_daily_summary;
            statusEl.innerHTML = d.is_verified
                ? '<span class="badge badge-active">✅ SMTP Verified</span>'
                : '<span class="badge badge-paused">⚠️ Not Verified — Send a test email</span>';
        } else {
            statusEl.innerHTML = '<span class="badge badge-expired">Not configured</span>';
        }
    } catch(err) { console.error(err); }
}

async function saveEmailConfig(e) {
    e.preventDefault();
    try {
        await api.post('/api/email/config', {
            smtp_provider: document.getElementById('smtp-provider').value,
            smtp_host: document.getElementById('smtp-host').value,
            smtp_port: parseInt(document.getElementById('smtp-port').value),
            smtp_username: document.getElementById('smtp-username').value,
            smtp_password: document.getElementById('smtp-password').value,
            sender_email: document.getElementById('sender-email').value,
            sender_name: document.getElementById('sender-name').value,
            enabled: true,
            notify_on_click: document.getElementById('notify-click').checked,
            notify_on_submit: document.getElementById('notify-submit').checked,
            notify_on_location: document.getElementById('notify-location').checked,
            notify_daily_summary: document.getElementById('notify-daily').checked,
        });
        showToast('Email configuration saved!', 'success');
        await loadEmailConfig();
    } catch(err) { showToast(err.message, 'error'); }
}

async function sendTestEmail() {
    try {
        const r = await api.post('/api/email/test');
        if (r.status === 'sent') {
            showToast('Test email sent successfully!', 'success');
            await loadEmailConfig();
        } else {
            showToast('Failed: ' + (r.error || 'Unknown error'), 'error');
        }
    } catch(err) { showToast(err.message, 'error'); }
}

// ── Notification Logs ────────────────────────────────────────────────
async function loadNotificationLogs() {
    try {
        const [logs, stats] = await Promise.all([
            api.get('/api/notifications'),
            api.get('/api/notifications/stats'),
        ]);
        document.getElementById('notif-total').textContent = stats.total;
        document.getElementById('notif-success').textContent = stats.sent;
        document.getElementById('notif-failed').textContent = stats.failed;

        const tb = document.getElementById('notification-logs-body');
        if (!logs.length) {
            tb.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted)">No notifications sent yet</td></tr>`;
            return;
        }
        tb.innerHTML = logs.map(n => `<tr>
            <td><span class="badge badge-active">${escHtml(n.notification_type)}</span></td>
            <td>${escHtml(n.recipient_email)}</td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(n.subject)}</td>
            <td><span class="badge ${n.status==='sent'?'badge-active':n.status==='failed'?'badge-expired':'badge-paused'}">${n.status}</span></td>
            <td>${n.sent_at ? new Date(n.sent_at).toLocaleString() : new Date(n.created_at).toLocaleString()}</td>
        </tr>`).join('');
    } catch(err) { showToast('Failed to load notifications', 'error'); }
}

// ── Audit Logs ───────────────────────────────────────────────────────
async function loadAuditLogs() {
    const logs = await api.get('/api/analytics/audit-logs');
    const tb = document.getElementById('audit-logs-body');
    if (!logs.length) { tb.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:40px;color:var(--text-muted)">No audit logs yet</td></tr>`; return; }
    tb.innerHTML = logs.map(l => `<tr>
        <td><span class="badge badge-active">${escHtml(l.action)}</span></td>
        <td>${escHtml(l.details)}</td>
        <td style="font-family:monospace">${l.ip_address || '—'}</td>
        <td>${new Date(l.timestamp).toLocaleString()}</td>
    </tr>`).join('');
}

// ── Modals ───────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('visible'); }
function closeModal(id) { document.getElementById(id).classList.remove('visible'); }

// ── Helpers ──────────────────────────────────────────────────────────
function escHtml(t) { const d = document.createElement('div'); d.textContent = t||''; return d.innerHTML; }
function copyText(t) { navigator.clipboard.writeText(t).then(() => showToast('Copied!', 'success')); }

// ── Render App ───────────────────────────────────────────────────────
function renderApp() {
    const login = document.getElementById('login-screen');
    const app = document.getElementById('app-layout');
    if (state.token) {
        login.style.display = 'none';
        app.style.display = 'flex';
        const un = document.getElementById('display-username');
        const av = document.getElementById('user-avatar-letter');
        if (un) un.textContent = state.username;
        if (av) av.textContent = (state.username||'A')[0].toUpperCase();
        navigate('dashboard');
        connectSSE();
    } else {
        login.style.display = 'flex';
        app.style.display = 'none';
    }
}

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', renderApp);
