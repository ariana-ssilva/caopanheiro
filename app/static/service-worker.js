/* Only explicitly listed public assets are stored. Pages and submissions never enter Cache Storage. */
const CACHE_PREFIX = 'caopanheiro-pwa-';
const CACHE_NAME = `${CACHE_PREFIX}v1`;
const OFFLINE_URL = '/static/pwa/offline.html';
const ASSETS = [
  OFFLINE_URL,
  '/static/pwa/icon-192.png',
  '/static/pwa/icon-512.png',
  '/static/pwa/icon-maskable-512.png',
  '/static/pwa/apple-touch-icon.png',
  '/static/favicon.svg',
  '/static/style.css',
  '/static/pwa.js',
  '/static/adoption.js',
  '/static/animal-form.js',
  '/static/photo-preview.js',
  '/static/navigation.js',
  '/static/vendor/fontawesome/css/fontawesome.min.css',
  '/static/vendor/fontawesome/css/solid.min.css',
  '/static/vendor/fontawesome/css/regular.min.css',
  '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
  '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2'
];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(ASSETS.map(path => new Request(path, { credentials: 'omit', cache: 'reload' })));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  // No interception of POSTs, external services or photos (including avatars).
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate') {
    // Private HTML stays on the network and is never written to the cache.
    event.respondWith(fetch(request).catch(async () => {
      const cache = await caches.open(CACHE_NAME);
      return await cache.match(OFFLINE_URL) || Response.error();
    }));
    return;
  }
  if (!ASSETS.includes(url.pathname) || url.search) return;
  // Network first keeps styles/scripts fresh after a deploy, with offline fallback.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      const response = await fetch(request);
      if (response.ok && !response.redirected && response.type !== 'opaque') {
        try { await cache.put(url.pathname, response.clone()); } catch (_) { /* Cache quota must not break online requests. */ }
      }
      return response;
    } catch (_) {
      return await cache.match(url.pathname) || Response.error();
    }
  })());
});
