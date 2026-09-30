import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';

test('website executes and reuses recorded experiments through the real API', async ({ page, request }) => {
  test.setTimeout(180000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/#/operations');
  await expect(page.getByRole('heading', { name: 'Choose an experiment' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Queue experiment', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Prepare example episodes', exact: true }).click();
  await expect(page.getByLabel('Frozen dataset', { exact: true })).not.toHaveValue('');
  const datasetId = await page.getByLabel('Frozen dataset', { exact: true }).inputValue();
  const submitted = page.waitForResponse(response => response.url().endsWith('/api/operations/jobs') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Queue experiment', exact: true }).click();
  const job = await (await submitted).json();
  const result = page.getByRole('region', { name: 'Model candidate', exact: true });
  await expect(result.getByText('Completed', { exact: true })).toBeVisible({ timeout: 120000 });
  await expect(result).toContainText('no model has been promoted');
  await expect(result.getByRole('table')).toContainText('Training climatology baseline');
  const completed = await (await request.get('/api/operations/jobs/' + job.id)).json();
  const duplicate = await (await request.post('/api/operations/jobs', { data: { kind: 'train_candidate', dataset_id: datasetId } })).json();
  expect([duplicate.id, duplicate.attempt, duplicate.finished_at]).toEqual([completed.id, completed.attempt, completed.finished_at]);
  expect(completed.summary.promoted).toBe(false);
  for (const artifact of completed.artifacts) {
    const response = await request.get(artifact.download_url);
    expect(response.ok()).toBe(true);
    const bytes = await response.body();
    expect(bytes.length).toBe(artifact.bytes);
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(artifact.sha256);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'artifacts/operations-desktop.png', fullPage: true });
  for (const [kind, title, expected] of [
    ['starter_audit', 'Source integrity', '18 of 18 source files verified'],
    ['radar_replay', 'Observed radar evaluation', 'This experiment has no lightning labels.'],
  ]) {
    await page.getByLabel('Experiment', { exact: true }).selectOption(kind);
    await page.getByRole('button', { name: 'Queue experiment', exact: true }).click();
    const recorded = page.getByRole('region', { name: title, exact: true });
    await expect(recorded.getByText('Completed', { exact: true })).toBeVisible({ timeout: 30000 });
    await expect(recorded).toContainText(expected);
  }
  const links = (await (await request.get('/api/operations/state')).json()).research;
  for (const reference of links) {
    const response = await request.get(reference.url);
    expect(response.ok()).toBe(true);
    expect(response.headers()['content-type']).toContain('text/markdown');
  }
  expect(errors).toEqual([]);
});

test('website preserves stale evidence, blocks writes and recovers at phone width', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/operations');
  await expect(page.getByRole('heading', { name: 'Recent experiments' })).toBeVisible();
  const records = page.locator('.operations-job');
  expect(await records.count()).toBeGreaterThan(0);
  await records.filter({ hasText: 'Model candidate' }).first().click();
  await expect(page.getByRole('table')).toContainText('Calibrated candidate');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'artifacts/operations-mobile.png', fullPage: true });
  await page.route('**/api/operations/state', route => route.abort('failed'));
  await page.getByRole('button', { name: 'Refresh operations', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Operations could not refresh.');
  await expect(page.getByRole('button', { name: 'Queue experiment', exact: true })).toBeDisabled();
  await expect(page.getByRole('table')).toContainText('Calibrated candidate');
  await page.screenshot({ path: 'artifacts/operations-offline.png', fullPage: true });
  await page.unroute('**/api/operations/state');
  const refresh = page.getByRole('button', { name: 'Refresh operations', exact: true });
  await refresh.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Queue experiment', exact: true })).toBeEnabled();
  expect(errors).toEqual([]);
});

test('an older repeated job remains selected outside the recent history projection', async ({ page, request }) => {
  const snapshot = await (await request.get('/api/operations/state')).json();
  const candidate = snapshot.jobs.find(job => job.kind === 'train_candidate' && job.status === 'succeeded');
  expect(candidate).toBeTruthy();
  // Controlled projection of a real store: emulate a candidate outside its recent 30 rows.
  await page.route('**/api/operations/state', route => route.fulfill({
    json: { ...snapshot, jobs: snapshot.jobs.filter(job => job.id !== candidate.id) },
  }));
  await page.goto('/#/operations');
  await page.getByRole('button', { name: 'Prepare example episodes', exact: true }).click();
  await expect(page.getByLabel('Frozen dataset', { exact: true })).not.toHaveValue('');
  await page.getByRole('button', { name: 'Queue experiment', exact: true }).click();
  const result = page.getByRole('region', { name: 'Model candidate', exact: true });
  await expect(result).toContainText(candidate.id);
  await expect(result).toContainText('Completed');
  await page.getByRole('button', { name: 'Refresh operations', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Refresh operations', exact: true })).toBeEnabled();
  await expect(result).toContainText(candidate.id);
  await expect(result.getByRole('table')).toContainText('Calibrated candidate');
});
