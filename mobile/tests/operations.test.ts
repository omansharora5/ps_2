import test from 'node:test';
import assert from 'node:assert/strict';
import { createOperationsMonitor, latestCandidate, parseOperations, recentJobs, utcTime, type OperationsSnapshot } from '../src/lib/operations.ts';
import { OPERATION_COPY_KEYS, operationDictionaries } from '../../shared/operation-translations.ts';
import { LANGUAGES, t } from '../../shared/translations.ts';

const time = '2026-09-30T10:00:00Z';
function candidate(overrides: Record<string, unknown> = {}) {
  return { mode: 'training_candidate', raw_brier: 0.15, calibrated_brier: 0.14, baseline_brier: 0.09, test_event_count: 8, recommendation: 'retain_baseline', promoted: false, ...overrides };
}
function job(overrides: Record<string, unknown> = {}) {
  return { id: 'candidate-1', kind: 'train_candidate', status: 'succeeded', stage: 'evaluation_complete', scope: 'synthetic_test', created_at: time, updated_at: time, error: null, summary: candidate(), ...overrides };
}
function fixture(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: 1, scope: 'research_only', writes_enabled: true,
    worker: { available: false, last_seen_at: null, current_job_id: null },
    learning: { enabled: false, status: 'disabled', note: 'No automatic promotion.', last_checked_at: null, last_job_id: null },
    datasets: [{ id: 'sample', name: 'Sample', scope: 'synthetic_test', event_count: 12, learning_eligible: false, readiness_reasons: ['Synthetic only.'], target: 'Simulated lightning' }],
    jobs: [job()], recipes: [], research: [], future_field: { ignored: true }, ...overrides,
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test('operations parser preserves research scope and finite candidate evidence without granting writes', () => {
  const data = parseOperations(fixture());
  assert.equal(data.scope, 'research_only');
  assert.equal('writes_enabled' in data, false);
  assert.equal(data.jobs[0].status, 'succeeded');
  assert.equal(data.jobs[0].summary?.recommendation, 'retain_baseline');
  assert.equal(data.jobs[0].summary?.promoted, false);
  assert.ok(data.jobs[0].summary!.calibrated_brier > data.jobs[0].summary!.baseline_brier);
  assert.equal(data.datasets[0].learning_eligible, false);
  assert.equal(parseOperations(fixture({ jobs: [], datasets: [] })).jobs.length, 0);
});

test('operations parser rejects unsupported scope, bad source data, duplicate IDs and ambiguous timestamps', () => {
  const invalid = [
    null, [], fixture({ schema_version: 2 }), fixture({ scope: 'operational' }), fixture({ jobs: {} }),
    fixture({ worker: { available: 'yes', last_seen_at: null } }),
    fixture({ worker: { available: true, last_seen_at: '2026-09-30T10:00:00' } }),
    fixture({ learning: { enabled: true, status: 'scheduled', note: '', last_checked_at: null } }),
    fixture({ datasets: [{ id: 'x', name: 'X', scope: 'unknown', event_count: Infinity, learning_eligible: true, readiness_reasons: [], target: 'T' }] }),
    fixture({ jobs: [job({ status: 'available' })] }), fixture({ jobs: [job({ kind: 'dispatch_alert' })] }),
    fixture({ jobs: [job({ created_at: '2026-09-30' })] }), fixture({ jobs: [job({ error: false })] }),
    fixture({ jobs: [job(), job()] }), fixture({ datasets: Array(101).fill({}) }),
  ];
  for (const value of invalid) assert.throws(() => parseOperations(value));
});

test('candidate boundary rejects impossible scores, no test events and automatic promotion', () => {
  const invalid = [
    { raw_brier: NaN }, { calibrated_brier: Infinity }, { baseline_brier: -0.1 }, { raw_brier: 1.1 },
    { baseline_brier: '0.2' }, { test_event_count: 0 }, { test_event_count: 2.5 },
    { recommendation: 'deploy' }, { promoted: true },
  ];
  for (const override of invalid) assert.throws(() => parseOperations(fixture({ jobs: [job({ summary: candidate(override) })] })));
  assert.equal(parseOperations(fixture({ jobs: [job({ summary: { mode: 'radar_replay', future_metric: Infinity } })] })).jobs[0].summary, null);
});

test('latest candidate requires successful training and uses issue order without assuming improvement', () => {
  const jobs = parseOperations(fixture({ jobs: [
    job({ id: 'older', created_at: '2026-09-29T10:00:00Z' }),
    job({ id: 'new-running', status: 'running', created_at: '2026-09-30T12:00:00Z' }),
    job({ id: 'new-failed', status: 'failed', created_at: '2026-09-30T13:00:00Z' }),
    job({ id: 'wrong-kind', kind: 'starter_audit', created_at: '2026-09-30T14:00:00Z' }),
    job({ id: 'latest-completed' }),
  ] })).jobs;
  assert.equal(latestCandidate(jobs)?.id, 'latest-completed');
  assert.equal(latestCandidate(jobs)?.summary?.recommendation, 'retain_baseline');
  assert.equal(recentJobs(jobs)[0].id, 'wrong-kind');
  assert.equal(jobs[0].id, 'older');
  assert.equal(latestCandidate(jobs.filter(item => item.status !== 'succeeded')), undefined);
  assert.equal(utcTime('2026-09-30T15:30:00+05:30'), '2026-09-30 10:00:00 UTC');
});

test('repeated refresh shares one request and does not create a job or a second request', async () => {
  const pending = deferred<unknown>(), states: OperationsSnapshot[] = [];
  let calls = 0;
  const monitor = createOperationsMonitor(async () => { calls += 1; return pending.promise; }, value => states.push(value), () => 42);
  const first = monitor.refresh(), second = monitor.refresh();
  assert.equal(first, second);
  await Promise.resolve();
  assert.equal(calls, 1);
  pending.resolve(fixture());
  await first;
  assert.deepEqual(states.map(item => item.phase), ['loading', 'ready']);
  assert.equal(states.at(-1)?.receivedAt, 42);
});

test('unreachable first request and invalid later response retain honest error and stale states', async () => {
  const states: OperationsSnapshot[] = [];
  let calls = 0;
  const monitor = createOperationsMonitor(async () => {
    calls += 1;
    if (calls === 1) throw new Error('offline');
    return calls === 2 ? fixture() : fixture({ scope: 'operational' });
  }, value => states.push(value), () => 17);
  await monitor.refresh();
  assert.equal(states.at(-1)?.phase, 'error');
  assert.equal(states.at(-1)?.data, null);
  await monitor.refresh();
  const good = states.at(-1);
  assert.equal(good?.phase, 'ready');
  await monitor.refresh();
  assert.equal(states.at(-1)?.phase, 'stale');
  assert.equal(states.at(-1)?.data, good?.data);
  assert.equal(states.at(-1)?.receivedAt, 17);
});

test('leaving the screen aborts work and an old response cannot overwrite a newer snapshot', async () => {
  const old = deferred<unknown>(), newer = deferred<unknown>(), states: OperationsSnapshot[] = [], signals: AbortSignal[] = [];
  const monitor = createOperationsMonitor(signal => { signals.push(signal); return signals.length === 1 ? old.promise : newer.promise; }, value => states.push(value));
  const first = monitor.refresh();
  await Promise.resolve();
  monitor.pause(); monitor.pause();
  assert.equal(signals[0].aborted, true);
  const next = monitor.refresh();
  await Promise.resolve();
  newer.resolve(fixture({ jobs: [] }));
  await next;
  old.resolve(fixture());
  await first;
  assert.equal(states.at(-1)?.data?.jobs.length, 0);
  assert.equal(states.at(-1)?.phase, 'ready');
  monitor.pause();
  assert.equal(states.at(-1)?.phase, 'stale');
  assert.equal(states.at(-1)?.data?.jobs.length, 0);
});

test('pause before request dispatch prevents an unnecessary fetch and permits clean restart', async () => {
  let calls = 0;
  const states: OperationsSnapshot[] = [];
  const monitor = createOperationsMonitor(async () => { calls += 1; return fixture(); }, value => states.push(value));
  const first = monitor.refresh(); monitor.pause();
  await first;
  assert.equal(calls, 0);
  assert.equal(states.at(-1)?.phase, 'idle');
  await monitor.refresh();
  assert.equal(calls, 1);
  assert.equal(states.at(-1)?.phase, 'ready');
});

test('all 13 operation locales cover statuses, stale snapshots and research-only caveats', () => {
  for (const { code } of LANGUAGES) {
    for (const key of OPERATION_COPY_KEYS) {
      assert.ok(operationDictionaries[code][key].trim());
      assert.doesNotMatch(operationDictionaries[code][key], /\uFFFD|\?{2,}/);
      assert.equal(t(code, key), operationDictionaries[code][key]);
    }
    if (code !== 'en') for (const key of ['opsReadOnly', 'opsStale', 'opsUnavailable', 'opsNotPromoted'] as const) assert.notEqual(operationDictionaries[code][key], operationDictionaries.en[key]);
  }
});
