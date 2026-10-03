import { useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:4000';

const defaultPrompt = 'What needs renewal this month?';

function App() {
  const [token, setToken] = useState(localStorage.getItem('personalos-token') || '');
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('personalos-user') || 'null'));
  const [form, setForm] = useState({ email: 'demo@personalos.ai', password: '' });
  const [dashboard, setDashboard] = useState({ renewals: [], health: [], stock: { portfolio: [], totalValue: 0 }, audit: [] });
  const [query, setQuery] = useState(defaultPrompt);
  const [response, setResponse] = useState({ agent: '', response: '', data: {} });
  const [loading, setLoading] = useState(false);

  const headers = useMemo(
    () => ({
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }),
    [token]
  );

  useEffect(() => {
    if (!token) return;
    localStorage.setItem('personalos-token', token);
    const loadData = async () => {
      try {
        const [renewals, health, stock, audit] = await Promise.all([
          fetch(`${API_BASE}/api/renewals`, { headers }),
          fetch(`${API_BASE}/api/health`, { headers }),
          fetch(`${API_BASE}/api/stock/summary`, { headers }),
          fetch(`${API_BASE}/api/audit-log`, { headers })
        ]);
        if ([renewals, health, stock, audit].some((res) => res.status === 401)) {
          logout();
          return;
        }
        const [renewalData, healthData, stockData, auditData] = await Promise.all(
          [renewals, health, stock, audit].map((res) => res.json())
        );

        setDashboard({
          renewals: renewalData.renewals || [],
          health: healthData.records || [],
          stock: stockData || { portfolio: [], totalValue: 0 },
          audit: auditData.entries || []
        });
      } catch (error) {
        console.error('Unable to load dashboard', error);
      }
    };

    loadData();
  }, [token, headers]);

  const login = async (event) => {
    event.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers,
        body: JSON.stringify(form)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || 'Login failed');

      localStorage.setItem('personalos-token', data.token);
      localStorage.setItem('personalos-user', JSON.stringify(data.user));
      setToken(data.token);
      setUser(data.user);
    } catch (error) {
      alert(error.message);
    }
  };

  const logout = () => {
    localStorage.removeItem('personalos-token');
    localStorage.removeItem('personalos-user');
    setToken('');
    setUser(null);
  };

  const sendPrompt = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/supervisor/route`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ query })
      });

      const data = await res.json();
      if (res.status === 401) { logout(); return; }
      setResponse(data);
    } catch (error) {
      setResponse({ agent: 'Error', response: 'Unable to reach the supervisor.' });
    } finally {
      setLoading(false);
    }
  };

  const recentRenewals = dashboard.renewals.slice(0, 3);
  const avgSleep = useMemo(() => {
    const sleep = dashboard.health.filter((item) => item.metric === 'sleep');
    if (!sleep.length) return 0;
    return sleep.reduce((total, item) => total + Number(item.value), 0) / sleep.length;
  }, [dashboard.health]);

  if (!user || !token) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <div className="brand-row">
            <div className="brand-mark">P</div>
            <div>
              <p className="eyebrow">Permission-aware supervisor</p>
              <h1>PersonalOS</h1>
            </div>
          </div>

          <form onSubmit={login} className="auth-form">
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
              />
            </label>

            <button type="submit">Access dashboard</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Supervisor</p>
          <h2>PersonalOS Console</h2>
        </div>

        <div className="topbar-user">
          <span>{user.name}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>

      <main className="dashboard-layout">
        <section className="metrics-grid">
          <article className="metric-card accent">
            <span className="label">Renewal watchlist</span>
            <strong>{recentRenewals.length}</strong>
            <small>Priority items</small>
          </article>

          <article className="metric-card accent-alt">
            <span className="label">Health trend</span>
            <strong>{avgSleep.toFixed(1)}h</strong>
            <small>Average sleep</small>
          </article>

          <article className="metric-card accent-dark">
            <span className="label">Portfolio value</span>
            <strong>₹{Number(dashboard.stock.totalValue || 0).toLocaleString('en-IN')}</strong>
            <small>Read-only analysis</small>
          </article>

          <article className="metric-card warning">
            <span className="label">Approval engine</span>
            <strong>Policy</strong>
            <small>Human review</small>
          </article>
        </section>

        <section className="panel-grid">
          <div className="panel">
            <div className="panel-header">
              <h3>Renewal agent</h3>
              <span className="pill success">Live</span>
            </div>
            <ul className="item-list">
              {recentRenewals.map((item) => (
                <li key={item.id}>
                  <div>
                    <strong>{item.name}</strong>
                    <small>{item.category}</small>
                  </div>
                  <span>{item.dueDate}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Health agent</h3>
              <span className="pill info">Sensitive</span>
            </div>
            <div className="health-summary">
              <p>Average sleep: <strong>{avgSleep.toFixed(1)} hours</strong></p>
              <p>Activity: <strong>{dashboard.health.filter((item) => item.metric === 'steps').length} tracked sessions</strong></p>
              <p className="note">AI interpretation is an advisory summary and not a diagnosis.</p>
            </div>
          </div>

          <div className="panel wide">
            <div className="panel-header">
              <h3>Supervisor chat</h3>
              <span className="pill neutral">Intent routing</span>
            </div>

            <form onSubmit={sendPrompt} className="chat-form">
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                rows={4}
                placeholder="Ask the supervisor..."
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Routing...' : 'Route request'}
              </button>
            </form>

            <div className="response-box">
              <small>{response.agent || 'No route yet'}</small>
              <p>{response.response || 'The supervisor will route your request to the correct agent.'}</p>
              {response.data && response.data.summary && <p>{response.data.summary}</p>}
            </div>
          </div>
        </section>

        <section className="bottom-grid">
          <div className="panel">
            <div className="panel-header">
              <h3>Portfolio analysis</h3>
              <span className="pill neutral">Read-only</span>
            </div>
            <ul className="portfolio-list">
              {(dashboard.stock.portfolio || []).map((item) => (
                <li key={item.symbol}>
                  <span>{item.symbol}</span>
                  <span>{item.shares} shares</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Audit log</h3>
              <span className="pill warning">Approved only</span>
            </div>
            <ul className="audit-list">
              {(dashboard.audit || []).slice(0, 4).map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.event}</strong>
                  <small>{new Date(entry.timestamp).toLocaleString()}</small>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;



