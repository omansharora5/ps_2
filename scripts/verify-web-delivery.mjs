import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await page.goto('http://127.0.0.1:8000/#/public');
  await page.evaluate(() => navigator.serviceWorker.ready);
  const session = await page.context().newCDPSession(page);
  const manifest = await session.send('Page.getAppManifest');
  const installability = await session.send('Page.getInstallabilityErrors');
  const documents = {};
  for (const name of ['PRODUCT_FLOW_AND_ALGORITHMS.md', 'JEV_ASSESSMENT.md', 'FRIEND_NOTES_REVIEW.md']) {
    const response = await page.request.get(`http://127.0.0.1:8000/research/${name}`);
    documents[name] = { status: response.status(), length: (await response.body()).length };
  }
  await page.keyboard.press('Tab');
  const skipLink = await page.getByRole('link', { name: 'Skip to content' }).evaluate(node => node === document.activeElement);
  await page.keyboard.press('Enter');
  const skipTarget = await page.locator('main').evaluate(node => node === document.activeElement);
  await page.goto('http://127.0.0.1:8000/#/flow');
  await page.screenshot({ path: 'artifacts/flow-desktop.png', fullPage: true });
  const report = { manifestErrors: manifest.errors, installability: installability.installabilityErrors, documents, skipLink, skipTarget };
  await writeFile('artifacts/web-delivery-check.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (manifest.errors.length || installability.installabilityErrors.length || !skipLink || !skipTarget || Object.values(documents).some(document => document.status !== 200)) process.exitCode = 1;
} finally {
  await browser.close();
}
