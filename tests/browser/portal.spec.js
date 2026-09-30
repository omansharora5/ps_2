import { test, expect } from '@playwright/test';

test('website routes explain current methods and keep the public preview distinct', async ({ page }) => {
  const errors = [];
  const forecasts = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.url().endsWith('/api/runs')) forecasts.push(request.url()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Understand the storm. Prepare with evidence.' })).toBeVisible();
  expect(forecasts).toHaveLength(0);
  await page.screenshot({ path: 'artifacts/overview-desktop.png', fullPage: true });
  await page.getByRole('link', { name: 'See how the predictions work' }).click();
  await expect(page).toHaveURL(/#\/flow$/);
  await expect(page.getByRole('heading', { name: 'Which prediction am I looking at?' })).toBeVisible();
  await expect(page.getByText('Global motion + image translation', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'From observations to a decision.' })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Understand the storm. Prepare with evidence.' })).toBeVisible();
  await page.getByRole('link', { name: 'Explore public preview' }).click();
  await expect(page.getByText('Design preview only.')).toBeVisible();
  await page.getByLabel('Explore a sample location').selectOption('Gaya');
  await expect(page.getByRole('heading', { name: 'Gaya', exact: true })).toBeVisible();
  expect(forecasts).toHaveLength(0);
  await page.screenshot({ path: 'artifacts/public-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.screenshot({ path: 'artifacts/public-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.getByRole('link', { name: 'Officer workbench', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Bihar study area · synthetic event' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle navigation' })).toHaveAttribute('aria-expanded', 'false');
  const bounds = await page.getByLabel('Data mode', { exact: true }).boundingBox();
  expect(bounds.height).toBeGreaterThanOrEqual(44);
  await page.screenshot({ path: 'artifacts/officer-mobile-updated.png', fullPage: true });
  for (const viewport of [{ width: 768, height: 1024 }, { width: 1024, height: 768 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(viewport);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '24px'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('saved simulation survives offline reload without caching live API data', async ({ page, context }) => {
  await page.goto('/#/workbench');
  await page.getByRole('button', { name: 'Save decision receipt' }).click();
  await expect(page.getByText('Saved locally')).toBeVisible();
  await page.getByRole('button', { name: 'View public preview' }).click();
  await expect(page.getByRole('heading', { name: 'Historical sample. Not a current warning.' })).toBeVisible();
  await expect(page.getByText('Sample issue time', { exact: true })).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText('Your device is offline.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Historical sample. Not a current warning.' })).toBeVisible();
  await page.getByRole('link', { name: 'How it works', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Read the observations', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Officer workbench', exact: true }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Bihar study area · synthetic event' })).not.toBeVisible();
  const cachePaths = await page.evaluate(async () => {
    const names = await caches.keys();
    return (await Promise.all(names.map(async name => (await (await caches.open(name)).keys()).map(request => new URL(request.url).pathname)))).flat();
  });
  expect(cachePaths.some(path => path.startsWith('/api/'))).toBe(false);
  await context.setOffline(false);
  await page.getByRole('button', { name: 'Retry request' }).click();
  await expect(page.getByRole('heading', { name: 'Bihar study area · synthetic event' })).toBeVisible();
  await page.getByRole('link', { name: 'Public preview', exact: true }).click();
  await page.getByRole('button', { name: 'Remove this saved sample' }).click();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Live weather information is unavailable.' })).toBeVisible();
});
