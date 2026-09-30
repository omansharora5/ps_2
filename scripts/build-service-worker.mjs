import { createHash } from 'node:crypto';
import { readdir, readFile, writeFile } from 'node:fs/promises';

const assets = (await readdir('dist/assets')).filter(name => /\.(js|css)$/.test(name)).map(name => `/assets/${name}`);
const files = ['/index.html', '/manifest.webmanifest', '/icon.svg', '/earth/blue-marble.jpg', '/earth/PROVENANCE.md', ...assets];
const hash = createHash('sha256').update('shell-v1');
for (const file of files) hash.update(await readFile(`dist${file}`));
const version = `vajra-shell-${hash.digest('hex').slice(0, 16)}`;
const script = `const CACHE = ${JSON.stringify(version)};
const FILES = ${JSON.stringify(files)};
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('vajra-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/research/')) return;
  if (event.request.mode === 'navigate' && ['/', '/index.html'].includes(url.pathname)) {
    event.respondWith(fetch(event.request).then(response => response.ok ? response : caches.match('/index.html')).catch(() => caches.match('/index.html')));
  } else if (FILES.includes(url.pathname)) {
    event.respondWith(caches.match(url.pathname).then(cached => cached || fetch(event.request)));
  }
});
`;
await writeFile('dist/sw.js', script);
console.log(`Offline app shell: ${files.length} files, ${version}`);
