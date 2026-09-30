import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { LANGUAGES, t } from '../shared/translations.ts';

const base = process.env.VAJRA_MOBILE_PREVIEW_URL || 'http://127.0.0.1:8152';
const api = process.env.VAJRA_TEST_API_URL || 'http://127.0.0.1:8140';
const state = await (await fetch(`${api}/api/community/state`)).json();
const browser = await chromium.launch({ headless: true });
const errors = [], checks = [], bodies = [], requests = [];
let page;
try {
  page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.url().includes('/api/community/')) requests.push({ url: request.url(), method: request.method() }); });
  await page.route('**/api/community/state*', route => {
    const selected = new URL(route.request().url()).searchParams.get('cell_id') || state.selected_cell;
    return route.fulfill({ json: { ...state, enabled: true, selected_cell: selected }, headers: { 'Access-Control-Allow-Origin': '*' } });
  });
  await page.route('**/api/community/reports', route => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'POST' } });
    bodies.push(route.request().postData());
    return route.fulfill({ status: bodies.length === 1 ? 503 : 200, json: bodies.length === 1 ? { detail: 'Controlled test outage' } : { report_id: 'native-runtime-test-only', status: 'recorded_unverified', duplicate: true, aggregate: state.aggregate }, headers: { 'Access-Control-Allow-Origin': '*' } });
  });
  await page.goto(base);
  await expect(page.getByText(t('en', 'communityTitle'), { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: t('en', 'communitySend'), exact: true })).toBeDisabled();
  await expect(page.getByRole('checkbox', { name: t('en', 'communityHere'), exact: true })).not.toBeChecked();
  await page.getByRole('radio', { name: state.cells[0].name, exact: true }).click();
  await page.getByRole('checkbox', { name: t('en', 'communityHere'), exact: true }).click();
  await page.getByRole('radio', { name: t('en', 'communityYes'), exact: true }).click();
  await page.getByRole('checkbox', { name: t('en', 'communityConsent'), exact: true }).click();
  await page.getByRole('button', { name: t('en', 'communitySend'), exact: true }).click();
  await expect(page.getByText(/Controlled test outage/)).toBeVisible();
  await expect(page.getByRole('radio', { name: t('en', 'communityNo'), exact: true })).toBeDisabled();
  checks.push('Native form requires explicit pilot cell, presence and answer; failed submission freezes the selected request');
  await page.reload();
  await expect(page.getByText(new RegExp(t('en', 'communityRestored').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))).toBeVisible();
  await page.getByRole('button', { name: t('en', 'retry'), exact: true }).first().click();
  await expect(page.getByText(/native-runtime-test-only/)).toBeVisible();
  expect(bodies).toHaveLength(2); expect(bodies[0]).toBe(bodies[1]);
  expect(Object.keys(JSON.parse(bodies[0])).sort()).toEqual(['answer', 'cell_id', 'consent_training', 'installation_id', 'observed_at_utc', 'request_id']);
  await page.reload(); await expect(page.getByText(/native-runtime-test-only/)).toBeVisible();
  checks.push('AsyncStorage restores the byte-identical retry and persisted unverified receipt; payload contains no GPS coordinates');
  await page.getByText(t('en', 'communityTitle'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-community-mocked-form.png' });
  await page.getByRole('button', { name: t('en', 'communityReset'), exact: true }).click();
  await expect(page.getByRole('checkbox', { name: t('en', 'communityHere'), exact: true })).not.toBeChecked();
  await expect(page.getByRole('button', { name: t('en', 'communitySend'), exact: true })).toBeDisabled();
  for (const language of ['hi', 'ur']) {
    await page.goto(`${base}/language`);
    await page.getByRole('button', { name: LANGUAGES.find(item => item.code === language).name, exact: true }).click();
    await expect(page.getByText(t(language, 'languageSaved'), { exact: true })).toBeVisible();
    await page.goto(base);
    await expect(page.getByText(t(language, 'communityQuestion'), { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: t(language, 'communitySend'), exact: true })).toBeDisabled();
    if (language === 'ur') await expect(page.getByText(t(language, 'communityQuestion'), { exact: true })).toHaveCSS('text-align', 'right');
  }
  checks.push('Explicit reset clears presence/answer and Hindi/Urdu reporting copy renders with Urdu text alignment');
  await page.getByText(t('ur', 'communityTitle'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-community-mocked-urdu.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  const result = { status: 'passed', checks, pageErrors: errors, scope: 'Chromium React Native web export; current API schema read from local backend, report responses mocked. No physical Android/iOS device, GPS, SMS delivery or operational forecast claim.' };
  await writeFile('artifacts/community-native-preview-check.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  if (page) await writeFile('artifacts/community-native-failure.txt', await page.locator('body').innerText());
  await writeFile('artifacts/community-native-preview-check.json', JSON.stringify({ status: 'failed', checks, pageErrors: errors, requests, error: String(error) }, null, 2));
  throw error;
} finally { await browser.close(); }
