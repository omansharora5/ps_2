import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  use: { baseURL: 'http://127.0.0.1:8000', viewport: { width: 1440, height: 1050 }, headless: true },
  workers: 1,
  reporter: 'list',
});
