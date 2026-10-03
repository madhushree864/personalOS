const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

const auditLog = [];
const renewals = [
  {
    id: 'r1',
    name: 'Health insurance premium',
    category: 'Insurance',
    dueDate: '2026-10-05',
    reminderDays: 18,
    status: 'upcoming'
  },
  {
    id: 'r2',
    name: 'Driving licence renewal',
    category: 'Government',
    dueDate: '2026-09-25',
    reminderDays: 5,
    status: 'upcoming'
  },
  {
    id: 'r3',
    name: 'Spotify Family',
    category: 'Subscription',
    dueDate: '2026-09-30',
    reminderDays: 10,
    status: 'upcoming'
  },
  {
    id: 'r4',
    name: 'Vehicle insurance',
    category: 'Insurance',
    dueDate: '2026-08-14',
    reminderDays: -18,
    status: 'overdue'
  }
];

const healthRecords = [
  { id: 'h1', date: '2026-09-10', metric: 'sleep', value: 7.2, unit: 'hours' },
  { id: 'h2', date: '2026-09-11', metric: 'sleep', value: 6.8, unit: 'hours' },
  { id: 'h3', date: '2026-09-12', metric: 'sleep', value: 7.9, unit: 'hours' },
  { id: 'h4', date: '2026-09-13', metric: 'heartRate', value: 68, unit: 'bpm' },
  { id: 'h5', date: '2026-09-14', metric: 'heartRate', value: 66, unit: 'bpm' },
  { id: 'h6', date: '2026-09-15', metric: 'steps', value: 9200, unit: 'steps' },
  { id: 'h7', date: '2026-09-16', metric: 'steps', value: 11850, unit: 'steps' }
];

const portfolio = [
  { symbol: 'AAPL', shares: 18, price: 214.44, allocation: 24 },
  { symbol: 'MSFT', shares: 12, price: 437.1, allocation: 20 },
  { symbol: 'NIFTY50', shares: 96, price: 24120, allocation: 18 },
  { symbol: 'RELIANCE', shares: 28, price: 2924, allocation: 16 }
];

const mockBroker = {
  status: 'sandbox',
  canExecute: false,
  lastApprovedBy: null,
  supported: ['AAPL', 'MSFT', 'NIFTY50', 'RELIANCE', 'HDFCBANK']
};

const user = {
  id: 'user-001',
  name: 'Aarav Sharma',
  email: 'demo@personalos.ai',
  password: process.env.DEMO_PASSWORD,
  role: 'user',
  permissions: ['renewal:read', 'renewal:write', 'health:read', 'stock:read', 'investment:review']
};

function logAudit(event, details = {}) {
  auditLog.unshift({
    id: uuidv4(),
    timestamp: new Date().toISOString(),
    event,
    details
  });
}

function getTokenFromHeader(req) {
  const auth = req.headers.authorization || '';
  if (!auth.startsWith('Bearer ')) return null;
  return auth.replace('Bearer ', '').trim();
}

function requireAuth(req, res, next) {
  const token = getTokenFromHeader(req);
  if (!token || token !== 'personalos-demo-token') {
    return res.status(401).json({ error: 'Authentication required' });
  }
  req.user = user;
  next();
}

function computeDaysRemaining(dateString) {
  const due = new Date(dateString);
  const today = new Date();
  const ms = due.getTime() - today.getTime();
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
}

function routeRequest(query) {
  const text = (query || '').toLowerCase();

  if (/(renew|insurance|subscription|membership|certificate|expiry|reminder)/.test(text)) {
    const response = `I found ${renewals.length} items that may need attention. The most urgent are ${renewals
      .slice()
      .sort((a, b) => computeDaysRemaining(a.dueDate) - computeDaysRemaining(b.dueDate))
      .slice(0, 2)
      .map((item) => `${item.name} (${computeDaysRemaining(item.dueDate)} days)`)
      .join(', ')}.`;

    return {
      agent: 'Renewal Agent',
      workflow: 'renewal',
      requiresHumanApproval: false,
      response,
      data: { renewals }
    };
  }

  if (/(health|heart|sleep|hrv|steps|weight|medical|lab|symptom|exercise|workout|doctor)/.test(text)) {
    const sleepValues = healthRecords.filter((item) => item.metric === 'sleep').map((item) => item.value);
    const avgSleep = sleepValues.reduce((sum, value) => sum + value, 0) / sleepValues.length;
    const avgSteps = healthRecords.filter((item) => item.metric === 'steps').map((item) => item.value);
    const stepAverage = avgSteps.reduce((sum, value) => sum + value, 0) / avgSteps.length;

    return {
      agent: 'Health Agent',
      workflow: 'health',
      requiresHumanApproval: false,
      response: 'Health data reviewed with privacy safeguards. Raw values are separated from the interpretation layer.',
      data: {
        rawData: healthRecords,
        statisticalObservation: {
          averageSleepHours: avgSleep.toFixed(1),
          averageSteps: stepAverage.toFixed(0),
          trend: 'Sleep quality is stable and step count is trending above the weekly baseline.'
        },
        aiInterpretation: {
          summary: 'Based on the captured trends, the user shows a consistent recovery pattern and moderate activity level. This is not a medical diagnosis and should be reviewed with a clinician for personalized advice.',
          safetyNote: 'AI interpretation is advisory only and must not replace professional medical guidance.'
        }
      }
    };
  }

  if (/(buy|sell|trade|broker|invest|money|transfer|withdraw|financial|cash|portfolio adjustment)/.test(text)) {
    return {
      agent: 'Investment Agent',
      workflow: 'investment',
      requiresHumanApproval: true,
      response: 'Investment requests require a policy review and explicit user confirmation before any broker action can be simulated.',
      data: {
        proposal: {
          action: 'Buy ₹10,000 of HDFCBANK',
          riskLevel: 'Medium',
          policyChecks: ['KYC status verified', 'Exposure within sandbox limit', 'User approval required'],
          broker: mockBroker
        }
      }
    };
  }

  if (/(stock|portfolio|company|equity|risk|market|analysis|financial report|compare)/.test(text)) {
    const totalValue = portfolio.reduce((sum, item) => sum + item.shares * item.price, 0);
    const risk = totalValue > 200000 ? 'Moderate' : 'Low';

    return {
      agent: 'Stock Analysis Agent',
      workflow: 'stock-analysis',
      requiresHumanApproval: false,
      response: 'Portfolio analysis generated without execution rights. This workflow is read-only and does not authorize any buy or sell action.',
      data: {
        holdings: portfolio,
        totalValue,
        risk,
        summary: 'The portfolio is diversified across technology and index exposure, with moderate concentration risk in large-cap equities.'
      }
    };
  }

  return {
    agent: 'Supervisor',
    workflow: 'general',
    requiresHumanApproval: false,
    response: 'I can help with renewals, health insights, stock analysis, or high-risk investment requests. Please tell me what you want to do.',
    data: {}
  };
}

app.get('/api/healthz', (_req, res) => {
  res.json({ status: 'ok', service: 'personalos-backend' });
});

app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password || email !== user.email || password !== user.password) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  logAudit('login', { email, success: true });
  res.json({
    token: 'personalos-demo-token',
    user: {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      permissions: user.permissions
    }
  });
});

app.get('/api/auth/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

app.get('/api/renewals', requireAuth, (_req, res) => {
  logAudit('renewals-read');
  res.json({ renewals });
});

app.post('/api/renewals', requireAuth, (req, res) => {
  const item = {
    id: uuidv4(),
    name: req.body.name,
    category: req.body.category || 'Custom',
    dueDate: req.body.dueDate,
    reminderDays: req.body.reminderDays || 7,
    status: 'upcoming'
  };

  renewals.unshift(item);
  logAudit('renewal-created', { item });
  res.status(201).json({ item });
});

app.put('/api/renewals/:id', requireAuth, (req, res) => {
  const index = renewals.findIndex((item) => item.id === req.params.id);
  if (index === -1) return res.status(404).json({ error: 'Renewal not found' });

  renewals[index] = { ...renewals[index], ...req.body };
  logAudit('renewal-updated', { renewal: renewals[index] });
  res.json({ renewal: renewals[index] });
});

app.delete('/api/renewals/:id', requireAuth, (req, res) => {
  const index = renewals.findIndex((item) => item.id === req.params.id);
  if (index === -1) return res.status(404).json({ error: 'Renewal not found' });

  const deleted = renewals.splice(index, 1)[0];
  logAudit('renewal-deleted', { deleted });
  res.json({ deleted });
});

app.get('/api/health', requireAuth, (_req, res) => {
  logAudit('health-read');
  res.json({ records: healthRecords });
});

app.post('/api/health', requireAuth, (req, res) => {
  const record = {
    id: uuidv4(),
    date: req.body.date || new Date().toISOString().slice(0, 10),
    metric: req.body.metric,
    value: Number(req.body.value),
    unit: req.body.unit || ''
  };

  healthRecords.unshift(record);
  logAudit('health-record-added', { record });
  res.status(201).json({ record });
});

app.post('/api/health/insights', requireAuth, (_req, res) => {
  const sleepValues = healthRecords.filter((item) => item.metric === 'sleep').map((item) => item.value);
  const avgSleep = sleepValues.reduce((sum, value) => sum + value, 0) / sleepValues.length;
  const latestSteps = healthRecords.filter((item) => item.metric === 'steps').slice(0, 2);

  const response = {
    sensitive: true,
    rawData: healthRecords,
    statisticalObservation: {
      averageSleepHours: avgSleep.toFixed(1),
      latestSteps: latestSteps.map((item) => ({ date: item.date, value: item.value }))
    },
    aiInterpretation: {
      summary: 'The observed pattern suggests the user has moderately stable sleep and activity data. Without doctor review, this remains an observational summary only.',
      caution: 'Do not treat these results as a diagnosis.'
    }
  };

  logAudit('health-insight-generated', { summary: response.aiInterpretation.summary });
  res.json(response);
});

app.get('/api/stock/summary', requireAuth, (_req, res) => {
  const totalValue = portfolio.reduce((sum, item) => sum + item.shares * item.price, 0);
  logAudit('stock-summary-read', { totalValue });
  res.json({ portfolio, totalValue, risk: 'Moderate' });
});

app.post('/api/stock/analyze', requireAuth, (req, res) => {
  const query = req.body?.query || 'portfolio';
  const analysis = routeRequest(query);
  logAudit('stock-analysis', { query, agent: analysis.agent });
  res.json(analysis);
});

app.post('/api/investment/propose', requireAuth, (req, res) => {
  const { symbol, amount, riskLevel } = req.body || {};
  const proposal = {
    status: 'pending_user_confirmation',
    symbol: symbol || 'HDFCBANK',
    amount: amount || 10000,
    riskLevel: riskLevel || 'Medium',
    broker: mockBroker,
    policyChecks: ['Sandbox mode enabled', 'User review required', 'Explicit approval before execution'],
    requiresHumanApproval: true
  };

  logAudit('investment-proposal', proposal);
  res.json({ proposal });
});

app.post('/api/investment/confirm', requireAuth, (req, res) => {
  const { approved, symbol, amount } = req.body || {};

  if (approved !== true) {
    logAudit('investment-rejected', { symbol, amount, approved: false });
    return res.json({ status: 'rejected', message: 'Execution not approved by user.' });
  }

  mockBroker.lastApprovedBy = req.user.name;
  mockBroker.canExecute = true;

  logAudit('investment-confirmed', { symbol, amount, approved: true });
  res.json({
    status: 'sandbox_execute',
    broker: mockBroker,
    message: 'Mock broker request is ready for execution in sandbox mode after MFA and audit verification.'
  });
});

app.post('/api/supervisor/route', requireAuth, (req, res) => {
  const query = req.body?.query || '';
  const result = routeRequest(query);
  logAudit('supervisor-routed', { query, agent: result.agent });
  res.json(result);
});

app.get('/api/audit-log', requireAuth, (_req, res) => {
  res.json({ entries: auditLog.slice(0, 10) });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`PersonalOS backend listening on http://localhost:${PORT}`);
  });
}

module.exports = {
  app,
  routeRequest,
  renewals,
  healthRecords,
  portfolio,
  auditLog,
  user
};
