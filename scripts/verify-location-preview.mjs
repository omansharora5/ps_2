import { chromium, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { t } from '../shared/translations.ts';

const base = process.env.VAJRA_MOBILE_PREVIEW_URL || 'http://127.0.0.1:8081';
const browser = await chromium.launch({ headless: true });
const checks = [];
const errors = [];
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    permissions: ['geolocation'],
    geolocation: { latitude: 51.5074, longitude: -0.1278, accuracy: 20 },
  });
  await context.addInitScript(() => {
    window.locationCalls = { position: 0, watch: 0, clear: 0, permission: 0 };
    window.activeLocationWatches = new Set();
    for (const [method, counter] of [['getCurrentPosition', 'position'], ['watchPosition', 'watch'], ['clearWatch', 'clear']]) {
      const original = navigator.geolocation[method].bind(navigator.geolocation);
      navigator.geolocation[method] = (...args) => {
        window.locationCalls[counter]++;
        const result = original(...args);
        if (method === 'watchPosition') window.activeLocationWatches.add(result);
        if (method === 'clearWatch') window.activeLocationWatches.delete(args[0]);
        return result;
      };
    }
    const query = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = descriptor => {
      if (descriptor.name === 'geolocation') window.locationCalls.permission++;
      return query(descriptor);
    };
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const requests = [];
  page.on('request', request => requests.push(`${request.url()} ${request.postData() || ''}`));
  await page.goto(base);
  await expect(page.getByText(t('en', 'homeTitle'), { exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.locationCalls)).toEqual({ position: 0, watch: 0, clear: 0, permission: 0 });
  checks.push('No location or permission query at public-screen startup');

  await page.getByRole('button', { name: t('en', 'useLocation'), exact: true }).click();
  await expect(page.getByText(t('en', 'locationReady'), { exact: true })).toBeVisible();
  await expect(page.getByText('51.5074°, -0.1278°', { exact: true })).toBeVisible();
  await expect(page.getByText(`${t('en', 'locationAccuracy')}: ±20 m`, { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'regionUnknown'), { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'liveCoverageUnavailable'), { exact: true })).toBeVisible();
  const calls = await page.evaluate(() => window.locationCalls);
  expect(calls.watch).toBe(1);
  expect(calls.clear).toBeGreaterThanOrEqual(1);
  expect(await page.evaluate(() => window.activeLocationWatches.size)).toBe(0);
  expect(requests.filter(value => value.includes('51.5074') || value.includes('-0.1278'))).toEqual([]);
  const storage = await page.evaluate(() => JSON.stringify({ ...localStorage }));
  expect(storage).not.toContain('51.5074');
  expect(storage).not.toContain('-0.1278');
  checks.push('Explicit request uses overridden London coordinates, reports uncertainty, stops subscription and makes no coordinate-bearing request');
  await page.screenshot({ path: 'artifacts/native-location-preview.png', fullPage: true });
  await page.getByText(t('en', 'regionUnknown'), { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'artifacts/native-location-details.png', fullPage: true });

  await page.getByLabel(t('en', 'search'), { exact: true }).fill('Mumbai');
  await page.getByRole('button', { name: 'Mumbai, Maharashtra', exact: true }).click();
  await expect(page.getByText('Mumbai', { exact: true })).toBeVisible();
  await expect(page.getByText(t('en', 'manualPointNote'), { exact: true })).toBeVisible();
  await expect(page.getByText('51.5074°, -0.1278°', { exact: true })).toHaveCount(0);
  checks.push('Manual city selection clears the device fix');

  await page.getByRole('button', { name: t('en', 'useLocation'), exact: true }).click();
  await expect(page.getByText(t('en', 'locationReady'), { exact: true })).toBeVisible();
  await page.getByRole('button', { name: t('en', 'clearLocation'), exact: true }).click();
  await expect(page.getByText('51.5074°, -0.1278°', { exact: true })).toHaveCount(0);
  checks.push('Clear-location control removes the fix');
  await context.close();

  const denied = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await denied.addInitScript(() => {
    const query = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = descriptor => descriptor.name === 'geolocation'
      ? Promise.resolve({ state: 'denied', onchange: null }) : query(descriptor);
  });
  const deniedPage = await denied.newPage();
  deniedPage.on('pageerror', error => errors.push(error.message));
  await deniedPage.goto(base);
  await deniedPage.getByRole('button', { name: t('en', 'useLocation'), exact: true }).click();
  await expect(deniedPage.getByText(t('en', 'locationDenied'), { exact: true })).toBeVisible();
  await deniedPage.getByLabel(t('en', 'search'), { exact: true }).fill('Mumbai');
  await deniedPage.getByRole('button', { name: 'Mumbai, Maharashtra', exact: true }).click();
  await expect(deniedPage.getByText('Mumbai', { exact: true })).toBeVisible();
  checks.push('Denied permission keeps the manual city flow usable');
  await denied.close();
  expect(errors).toEqual([]);
  const report = { status: 'passed', checks, pageErrors: errors, scope: 'Chromium React Native web export; browser-overridden location and mocked denied permission, not physical-phone GPS or native permission-dialog verification' };
  await writeFile('artifacts/location-preview-check.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await writeFile('artifacts/location-preview-check.json', JSON.stringify({ status: 'failed', checks, pageErrors: errors, error: String(error) }, null, 2));
  throw error;
} finally {
  await browser.close();
}
