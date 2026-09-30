import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { LANGUAGES, t } from '../shared/translations.ts';

// Run against the exported React Native web client, configured for the local API.
// These checks do not certify native installation, device voices or audible speech.
const base = process.env.VAJRA_MOBILE_PREVIEW_URL || 'http://127.0.0.1:8081';
const browser = await chromium.launch({ headless: true });
const checks = [];
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    Object.defineProperty(window.speechSynthesis, 'getVoices', { value: () => [] });
  });
  await page.goto(base);
  await expect(page.getByText(t('en', 'homeTitle'), { exact: true })).toBeVisible();
  for (const key of ['publicView', 'operatorView', 'language']) {
    const label = await page.getByText(t('en', key), { exact: true }).boundingBox();
    expect(label).not.toBeNull();
    expect(label.y + label.height).toBeLessThanOrEqual(844);
  }
  await page.getByLabel(t('en', 'search'), { exact: true }).fill('Mumbai');
  await page.getByRole('button', { name: 'Mumbai, Maharashtra', exact: true }).click();
  await expect(page.getByText('Mumbai', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: t('en', 'pauseMotion'), exact: true }).click();
  await expect(page.getByRole('button', { name: t('en', 'resumeMotion'), exact: true })).toBeVisible();
  checks.push('Public screen, city selection and motion pause');
  await page.evaluate(() => { for (const node of document.querySelectorAll('*')) if (node.scrollHeight > node.clientHeight) node.scrollTop = 0; });
  await page.screenshot({ path: 'artifacts/native-earth-preview.png', fullPage: true });
  await page.getByRole('button', { name: t('en', 'listen'), exact: true }).click();
  await expect(page.getByText(t('en', 'voiceFailed'), { exact: true })).toBeVisible();
  checks.push('Unresolved browser voice discovery times out to readable fallback');
  await page.screenshot({ path: 'artifacts/native-public-preview.png', fullPage: true });

  await page.goto(`${base}/language`);
  for (const language of LANGUAGES) await expect(page.getByRole('button', { name: language.name, exact: true })).toBeVisible();
  await page.getByRole('button', { name: LANGUAGES.find(item => item.code === 'hi').name, exact: true }).click();
  await expect(page.getByText(t('hi', 'languageSaved'), { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText(t('hi', 'practiceBody'), { exact: true })).toBeVisible();
  await page.screenshot({ path: 'artifacts/native-hindi-preview.png', fullPage: true });
  await page.getByRole('button', { name: LANGUAGES.find(item => item.code === 'ur').name, exact: true }).click();
  await expect(page.getByText(t('ur', 'practiceBody'), { exact: true })).toHaveCSS('text-align', 'right');
  await page.screenshot({ path: 'artifacts/native-urdu-preview.png', fullPage: true });
  checks.push('13 language choices, persisted Hindi preference and Urdu text alignment');
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByText(t('en', 'languageSaved'), { exact: true })).toBeVisible();

  await page.goto(`${base}/operator`);
  await expect(page.getByText('Indian observations and NASA context', { exact: true })).toBeVisible({ timeout: 20000 });
  await page.getByRole('button', { name: t('en', 'runSimulation'), exact: true }).click();
  await expect(page.getByText('Nalanda demo site', { exact: true })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText(/Target: Any simulated flash within 8 km/)).toBeVisible();
  await expect(page.getByText(/Lead: \+30 min/)).toBeVisible();
  await expect(page.getByText(t('en', 'simulationBody'), { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'artifacts/native-operator-preview.png', fullPage: true });
  checks.push('Real backend catalogue and labelled simulation, no document overflow');

  await page.route('**/api/data/catalog', route => route.abort());
  await page.reload();
  await expect(page.getByText(t('en', 'apiError'), { exact: true })).toBeVisible({ timeout: 20000 });
  await page.unroute('**/api/data/catalog');
  await page.getByRole('button', { name: t('en', 'retry'), exact: true }).click();
  await expect(page.getByText('Indian observations and NASA context', { exact: true })).toBeVisible();
  checks.push('API outage shows failure; retry restores catalogue');
  expect(errors).toEqual([]);
  const report = { status: 'passed', checks, pageErrors: errors, scope: 'Chromium preview of React Native web export; no native audio or installation claim' };
  await writeFile('artifacts/mobile-preview-check.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await writeFile('artifacts/mobile-preview-check.json', JSON.stringify({ status: 'failed', checks, pageErrors: errors, error: String(error) }, null, 2));
  throw error;
} finally {
  await browser.close();
}
