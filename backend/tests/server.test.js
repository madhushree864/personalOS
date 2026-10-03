const test = require('node:test');
const assert = require('node:assert/strict');

const { routeRequest } = require('../server');

test('renewal requests route to the Renewal Agent', () => {
  const result = routeRequest('What needs renewal this month?');
  assert.equal(result.agent, 'Renewal Agent');
  assert.equal(result.workflow, 'renewal');
});

test('health prompts keep the interpretation separated from raw data', () => {
  const result = routeRequest('Summarize my sleep and heart trends');
  assert.equal(result.agent, 'Health Agent');
  assert.ok(Array.isArray(result.data.rawData));
  assert.ok(result.data.aiInterpretation.summary.includes('not a medical diagnosis'));
});

test('investment requests require human approval', () => {
  const result = routeRequest('Buy ₹10,000 of HDFCBANK');
  assert.equal(result.agent, 'Investment Agent');
  assert.equal(result.requiresHumanApproval, true);
});
