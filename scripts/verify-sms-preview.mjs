import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { t } from '../shared/translations.ts';

const base = process.env.VAJRA_MOBILE_PREVIEW_URL || 'http://127.0.0.1:8081';
const browser = await chromium.launch({ headless: true });
const checks = [];
const errors = [];
const requests = [];
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push({ url: request.url(), body: request.postData() }));
  await page.goto(base);
  const place = page.getByLabel(t('en', 'reportPlace'), { exact: true });
  const note = page.getByLabel(t('en', 'reportNote'), { exact: true });
  await expect(place).toHaveValue('');
  await expect(note).toHaveValue('');
  await page.getByLabel(t('en', 'search'), { exact: true }).fill('Mumbai');
  await page.getByRole('button', { name: 'Mumbai, Maharashtra', exact: true }).click();
  await expect(place).toHaveValue('');
  await expect(page.getByRole('button', { name: t('en', 'reportOpenSms'), exact: true })).toBeDisabled();
  await expect(page.getByText(t('en', 'reportRequired'), { exact: true }).first()).toBeVisible();
  checks.push('Manual locality starts empty and city selection does not add a location to the report');
  await place.fill('Pilot field beside the old water tank');
  await note.fill('Test observation: strong gust at 16:10. This is a test, not a live report.');
  const preview = page.getByText(/Unverified citizen observation\s+Locality:/);
  await expect(preview).toContainText('This is not an official warning. Please verify this observation.');
  await expect(preview).toContainText('Pilot field beside the old water tank');
  await page.getByRole('button', { name: t('en', 'reportOpenSms'), exact: true }).click();
  await expect(page.getByText(t('en', 'reportUnavailable'), { exact: true })).toBeVisible();
  await expect(place).toHaveValue('Pilot field beside the old water tank');
  expect(await note.inputValue()).toContain('This is a test, not a live report.');
  await expect(preview).toBeVisible();
  checks.push('Actual web SMS-unavailable path retains the labelled unverified draft and editable fields');
  expect(JSON.stringify(requests)).not.toContain('Pilot field beside');
  expect(JSON.stringify(requests)).not.toContain('Test observation:');
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage }));
  expect(stored).not.toContain('Pilot field beside');
  expect(stored).not.toContain('Test observation:');
  checks.push('Report text was not sent to a network endpoint or saved in localStorage');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByText(t('en', 'reportTitle'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-sms-preview.png' });
  await page.getByText(t('en', 'reportUnavailable'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-sms-result.png' });
  expect(errors).toEqual([]);
  const report = { status: 'passed', checks, pageErrors: errors, scope: 'Exported React Native web client. No physical composer, SMS transmission, delivery or Bluetooth test.' };
  await writeFile('artifacts/sms-preview-check.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await writeFile('artifacts/sms-preview-check.json', JSON.stringify({ status: 'failed', checks, pageErrors: errors, error: String(error) }, null, 2));
  throw error;
} finally {
  await browser.close();
}
