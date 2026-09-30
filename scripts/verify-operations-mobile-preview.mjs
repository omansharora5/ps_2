import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { LANGUAGES, t } from '../shared/translations.ts';
import { latestCandidate, parseOperations } from '../mobile/src/lib/operations.ts';

const base = process.env.VAJRA_MOBILE_PREVIEW_URL || 'http://127.0.0.1:8081';
const browser = await chromium.launch({ headless: true });
const checks = [], errors = [], requests = [];
let observedCandidate = null;
const time = '2026-09-30T10:00:00Z';
const fixture = {
  schema_version: 1, scope: 'research_only', writes_enabled: true,
  worker: { available: false, last_seen_at: null, current_job_id: null },
  learning: { enabled: true, status: 'waiting_for_labels', note: 'Fixture: confirmed labels are not ready.', last_checked_at: time, last_job_id: null },
  datasets: [{ id: 'fixture-dataset', name: 'Fixture synthetic events', scope: 'synthetic_only', event_count: 24, learning_eligible: false, readiness_reasons: ['Fixture: Indian validation unavailable.'], target: 'Simulated lightning' }],
  jobs: [{
    id: 'fixture-completed-candidate', kind: 'train_candidate', status: 'succeeded', stage: 'evaluation_complete', scope: 'synthetic_only', dataset_id: 'fixture-dataset', attempt: 1,
    created_at: time, updated_at: time, started_at: time, finished_at: time, error: null, artifacts: [],
    summary: { mode: 'training_candidate', raw_brier: 0.15, calibrated_brier: 0.14, baseline_brier: 0.09, test_event_count: 8, recommendation: 'retain_baseline', promoted: false },
  }], recipes: [], research: [],
};
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().includes('/api/operations/')) requests.push({ url: request.url(), method: request.method(), body: request.postData() });
  });
  const initialResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/operations/state');
  await page.goto(`${base}/operator`);
  const actualState = parseOperations(await (await initialResponse).json());
  await expect(page.getByText(t('en', 'opsTitle'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsWorker'), { exact: true })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText(t('en', 'opsReadOnly'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'currentUnavailable'), { exact: true })).toBeVisible();
  await expect(page.getByText(new RegExp(t('en', 'opsSnapshot').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))).toBeVisible();
  checks.push('Actual operations API loads into the native web export; research-only, read-only and warning-disconnection scope remain visible');
  await page.getByText(t('en', 'opsTitle'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-operations-live.png' });
  const actualCandidate = latestCandidate(actualState.jobs);
  expect(actualCandidate?.summary).not.toBeNull();
  expect(actualCandidate).toBeDefined();
  const actualMetrics = actualCandidate.summary;
  await expect(page.getByText(actualMetrics.calibrated_brier.toFixed(5), { exact: true }).first()).toBeVisible();
  await expect(page.getByText(actualMetrics.baseline_brier.toFixed(5), { exact: true }).first()).toBeVisible();
  await expect(page.getByText(t('en', actualMetrics.recommendation === 'retain_baseline' ? 'opsRetain' : 'opsReview'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsNotPromoted'), { exact: true })).toBeVisible();
  observedCandidate = { id: actualCandidate.id, scope: actualCandidate.scope, ...actualMetrics };
  await page.getByText(t('en', 'opsCandidate'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-operations-live-candidate.png' });
  checks.push('Actual worker-completed candidate metrics and no-promotion result match the API response');

  await page.route('**/api/operations/state', route => route.fulfill({ json: fixture }));
  await page.getByRole('button', { name: t('en', 'opsRefresh'), exact: true }).click();
  await expect(page.getByText(t('en', 'opsRetain'), { exact: true })).toBeVisible();
  await expect(page.getByText('0.14000', { exact: true })).toBeVisible();
  await expect(page.getByText('0.09000', { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsNotPromoted'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsSucceeded'), { exact: true })).toBeVisible();
  await expect(page.getByText('Fixture synthetic events', { exact: true })).toBeVisible();
  checks.push('Controlled completed-job fixture displays worse-than-baseline Brier scores, retained baseline and no promotion');
  await page.getByText(t('en', 'opsCandidate'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-operations-candidate.png' });

  await page.unroute('**/api/operations/state');
  await page.route('**/api/operations/state', route => route.abort());
  await page.getByRole('button', { name: t('en', 'opsRefresh'), exact: true }).click();
  await expect(page.getByText(t('en', 'opsStale'), { exact: true })).toBeVisible();
  await expect(page.getByText('0.14000', { exact: true })).toBeVisible();
  checks.push('Failed refresh marks the retained snapshot stale and preserves the last good candidate');
  await page.getByText(t('en', 'opsStale'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-operations-stale.png' });
  await page.reload();
  await expect(page.getByText(t('en', 'opsUnavailable'), { exact: true })).toBeVisible();
  await expect(page.getByText('0.14000', { exact: true })).toHaveCount(0);
  checks.push('An initial API outage displays an error without invented jobs or persisted old metrics');

  await page.unroute('**/api/operations/state');
  await page.route('**/api/operations/state', route => route.fulfill({ json: { ...fixture, jobs: [], datasets: [] } }));
  await page.getByRole('button', { name: t('en', 'opsRefresh'), exact: true }).click();
  await expect(page.getByText(t('en', 'opsNoJobs'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsNoDatasets'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsNoCandidate'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'opsUnavailable'), { exact: true })).toHaveCount(0);
  checks.push('Explicit retry recovers to honest empty job, dataset and candidate states');

  for (const code of ['hi', 'ur']) {
    await page.goto(`${base}/language`);
    await page.getByRole('button', { name: LANGUAGES.find(item => item.code === code).name, exact: true }).click();
    await expect(page.getByText(t(code, 'languageSaved'), { exact: true })).toBeVisible();
    await page.goto(`${base}/operator`);
    await expect(page.getByText(t(code, 'opsTitle'), { exact: true })).toBeVisible();
    await expect(page.getByText(t(code, 'opsNoJobs'), { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: t(code, 'opsRefresh'), exact: true })).toBeVisible();
    if (code === 'ur') await expect(page.getByText(t(code, 'opsReadOnly'), { exact: true })).toHaveCSS('text-align', 'right');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  checks.push('Hindi operation labels and Urdu right-aligned read-only guidance render without document overflow');
  expect(requests.length).toBeGreaterThan(0);
  expect(requests.every(request => request.method === 'GET' && request.body === null && new URL(request.url).pathname === '/api/operations/state' && new URL(request.url).search === '')).toBe(true);
  expect(errors).toEqual([]);
  const report = { verified_at_utc: new Date().toISOString(), status: 'passed', checks, pageErrors: errors, operationsRequests: requests.length, observedCandidate, scope: 'Chromium React Native web export: real backend initial read and completed worker candidate, then explicitly labelled controlled fixtures for quality/failure/empty states. No native installation, jobs submitted, automatic training or public dispatch.' };
  await writeFile('artifacts/operations-mobile-preview-check.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await writeFile('artifacts/operations-mobile-preview-check.json', JSON.stringify({ verified_at_utc: new Date().toISOString(), status: 'failed', checks, pageErrors: errors, error: String(error) }, null, 2) + '\n');
  throw error;
} finally {
  await browser.close();
}
