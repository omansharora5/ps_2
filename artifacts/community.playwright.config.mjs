import base from '../playwright.config.js';
export default { ...base, testDir: '../tests/browser', use: { ...base.use, baseURL: 'http://127.0.0.1:8151', serviceWorkers: 'block' } };
