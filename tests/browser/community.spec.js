import { test, expect } from '@playwright/test';

const aggregate = { public_status: 'collecting', counts_withheld: true, independent_people_verified: false, automatic_training: false };
const fixture = (enabled = true) => ({ enabled, cells: [{ id: 'delhi-central', name: 'Central Delhi pilot cell', bbox: [77.1875, 28.5875, 77.2125, 28.6125] }, { id: 'noida', name: 'Noida pilot cell', bbox: [77.3, 28.5, 77.4, 28.6] }], selected_cell: 'delhi-central', prompt: { question: 'Is it raining where you are now?', forecast_status: 'unavailable', window_start_utc: '2026-09-30T12:00:00Z', window_end_utc: '2026-09-30T12:15:00Z' }, aggregate, evidence_card: { status: 'unavailable', rain_probability: null, lightning_probability: null, onset_interval: null, confidence: 'unvalidated', sensors: [{ id: 'radar', name: 'IMD radar', observed_at_utc: null, age_minutes: null, status: 'missing', note: 'Raw scans are not connected.' }], tracks: [], reasons: ['No validated NCR forecast is registered.'] }, scorecard: { status: 'unavailable', month: '2026-09', metrics: null, reason: 'No eligible observed test cases published.' }, benchmark: { status: 'metadata_only', raw_release_allowed: false, blockers: ['Raw radar redistribution rights are not established.'] } });
async function mockState(page, enabled = true) {
  await page.route('**/api/community/state*', route => {
    const data = fixture(enabled); data.selected_cell = new URL(route.request().url()).searchParams.get('cell_id') || 'delhi-central';
    return route.fulfill({ json: data });
  });
}
async function fillReport(page) {
  await page.getByRole('combobox', { name: 'Your current pilot cell', exact: true }).selectOption('delhi-central');
  await page.getByLabel('I am in the selected pilot cell.', { exact: true }).check();
  await page.getByRole('radio', { name: 'Yes', exact: true }).check();
  await page.getByLabel('Allow my report to be reviewed for research training.', { exact: true }).check();
}

test('community has an explicit location gate and honest unavailable evidence', async ({ page }) => {
  await mockState(page, false); await page.goto('/#/community');
  await expect(page.getByRole('heading', { name: 'Local rain evidence', exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Your current pilot cell', exact: true })).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Send observation', exact: true })).toBeDisabled();
  await expect(page.getByText('Reporting is not enabled on this service.', { exact: true })).toBeVisible();
  await expect(page.getByText('No verified monthly scores yet.', { exact: true })).toBeVisible();
  await expect(page.getByText('Unknown — no verified onset interval', { exact: true })).toBeVisible();
  await expect(page.getByText('Raw dataset release is not permitted yet.', { exact: true })).toBeVisible();
  await expect(page.getByText('Age unknown', { exact: true })).toBeVisible();
  await expect(page.locator('.community-page')).toContainText('Exact vote counts and report identities are withheld publicly');
});

test('failed submission survives reload and retries byte-identical data; reset is explicit', async ({ page }) => {
  await mockState(page); const requests = [];
  await page.route('**/api/community/reports', route => {
    requests.push(route.request().postData());
    return requests.length === 1 ? route.fulfill({ status: 503, json: { detail: 'Test connection failure' } }) : route.fulfill({ json: { report_id: 'report-test-1', status: 'recorded_unverified', duplicate: true, aggregate } });
  });
  await page.goto('/#/community'); await fillReport(page);
  await page.getByRole('button', { name: 'Send observation', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Test connection failure');
  await expect(page.getByRole('radio', { name: 'No', exact: true })).toBeDisabled();
  await page.reload(); await expect(page.getByText(/Saved report restored/)).toBeVisible();
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Recorded as unverified evidence.' })).toBeVisible();
  expect(requests).toHaveLength(2); expect(requests[0]).toBe(requests[1]);
  const request = JSON.parse(requests[0]); expect(Object.keys(request).sort()).toEqual(['answer', 'cell_id', 'consent_training', 'installation_id', 'observed_at_utc', 'request_id']);
  await page.reload(); await expect(page.getByRole('status').filter({ hasText: 'Recorded as unverified evidence.' })).toBeVisible();
  await page.getByRole('button', { name: 'Start a new observation', exact: true }).click();
  await expect(page.getByRole('radio', { name: 'Yes', exact: true })).not.toBeChecked();
  await expect(page.getByLabel('I am in the selected pilot cell.', { exact: true })).not.toBeChecked();
});

test('phone layout supports Urdu and operator queue rejection does not grant a role', async ({ page }) => {
  await mockState(page); await page.route('**/api/community/review-queue', route => route.fulfill({ status: 403, json: { detail: 'Local operator access required.' } }));
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/#/community');
  await page.getByLabel('Report language', { exact: true }).selectOption('ur');
  await expect(page.locator('[aria-labelledby="community-report-heading"]')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByText('کیا آپ کے یہاں ابھی بارش ہو رہی ہے؟', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByText('Local operator review', { exact: true }).click();
  await page.getByRole('button', { name: 'Load private review queue', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Local operator access required.');
  await expect(page.getByRole('button', { name: 'Record review', exact: true })).toBeDisabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'artifacts/community-mobile-mocked-urdu.png', fullPage: true });
});

test('published scorecard displays only supplied metrics and a matched comparator', async ({ page }) => {
  const data = fixture(); const metrics = { case_count: 20, event_count: 4, pod: .75, far: .25, csi: .6, brier: .18, reliability: [{ count: 20, mean_probability: .6, observed_frequency: .55 }] };
  data.scorecard = { status: 'published', month: '2026-09', model_id: 'test-fixture-only', hazard: 'rain', publication_cutoff: '2026-09-30T12:00:00Z', metrics, comparison: { name: 'Comparator test fixture', matched_cases: 20, model: metrics, comparator: { ...metrics, brier: null } } };
  await page.route('**/api/community/state*', route => route.fulfill({ json: data }));
  await page.goto('/#/community'); await expect(page.getByRole('img', { name: /Reliability:/ })).toBeVisible();
  await expect(page.getByText('Our model · same 20 cases', { exact: true })).toBeVisible();
  await expect(page.getByText('Comparator test fixture · identical cases', { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'artifacts/community-desktop-mocked-scorecard.png', fullPage: true });
});

test('operator review uses the selected private revision and keeps open windows out of approval', async ({ page }) => {
  await mockState(page);
  const window = { cell_id: 'delhi-central', window_start_utc: '2026-09-30T11:00:00Z', window_end_utc: '2026-09-30T11:15:00Z', revision: 'private-revision', yes: 5, no: 0, unsure: 0, consenting_reports: 5, review_status: 'pending', window_closed: false, reviewable_after_utc: '2026-09-30T11:30:00Z' };
  await page.route('**/api/community/review-queue', route => route.fulfill({ json: { windows: [window], automatic_training: false } }));
  let submitted;
  await page.route('**/api/community/review', route => { submitted = route.request().postDataJSON(); return route.fulfill({ json: { status: 'rejected' } }); });
  await page.goto('/#/community'); await page.getByText('Local operator review', { exact: true }).click();
  await page.getByRole('button', { name: 'Load private review queue', exact: true }).click();
  await page.getByRole('combobox', { name: 'Reporting window', exact: true }).selectOption(`${window.cell_id}/${window.window_start_utc}`);
  await page.getByRole('combobox', { name: 'Review decision', exact: true }).selectOption('approve');
  await expect(page.getByRole('button', { name: 'Record review', exact: true })).toBeDisabled();
  await page.getByRole('combobox', { name: 'Review decision', exact: true }).selectOption('reject');
  await page.getByRole('textbox', { name: 'Review reason', exact: true }).fill('Independent observations conflict with these reports.');
  await page.getByRole('button', { name: 'Record review', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Review recorded for this exact evidence revision.' })).toBeVisible();
  expect(submitted.expected_revision).toBe(window.revision);
  expect(submitted.window_start_utc).toBe(window.window_start_utc);
  expect(submitted.decision).toBe('reject');
});

test('live community service keeps missing forecast data honest at desktop and phone widths', async ({ page }) => {
  test.skip(!process.env.COMMUNITY_LIVE_URL, 'Set COMMUNITY_LIVE_URL for an actual local backend integration check.');
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(`${process.env.COMMUNITY_LIVE_URL}/#/community`);
  await expect(page.getByRole('heading', { name: 'Local rain evidence', exact: true })).toBeVisible();
  await expect(page.getByText('Exact vote counts and report identities are withheld publicly.', { exact: false })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Your current pilot cell', exact: true })).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Send observation', exact: true })).toBeDisabled();
  await expect(page.getByText('No verified monthly scores yet.', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'artifacts/community-desktop-live.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'artifacts/community-mobile-live.png', fullPage: true });
  expect(errors).toEqual([]);
});
