/**
 * Akamonkai Japanese — Service Worker
 * Cache-first strategy for offline PWA support
 */

const BUILD_ID = '20260507055649';
const CACHE_NAME = `akamonkai-${BUILD_ID}`;

// Core files to precache
const PRECACHE_URLS = [
  './',
  './index.html',
  './worksheets.html',
  './css/style.css',
  './js/app.js',
  './lesson-data.json',
  './manifest.json',
  './offline-asset-report.json',
  './precache-manifest.json',
];

async function getGeneratedPrecacheUrls() {
  try {
    const response = await fetch('./precache-manifest.json', { cache: 'no-store' });
    if (!response.ok) return [];
    const payload = await response.json();
    if (!Array.isArray(payload.urls)) return [];
    return payload.urls.filter(Boolean);
  } catch {
    return [];
  }
}

// Install: precache core files, then background-cache all assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // Always precache core files first
      await cache.addAll(PRECACHE_URLS);

      // Then try to cache generated assets (lessons, images, PDFs, audio)
      const generatedUrls = await getGeneratedPrecacheUrls();
      // Cache in batches to avoid overwhelming the browser
      const BATCH = 50;
      for (let i = 0; i < generatedUrls.length; i += BATCH) {
        const batch = generatedUrls.slice(i, i + BATCH);
        try {
          await cache.addAll(batch);
        } catch (e) {
          // Cache individually on batch failure so one bad URL doesn't skip all
          for (const url of batch) {
            try { await cache.add(url); } catch { /* skip */ }
          }
        }
      }
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: cache-first for static, network-first for API
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Don't cache API calls
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request).catch(() => {
      return new Response('{"error":"offline"}', {
        headers: { 'Content-Type': 'application/json' }
      });
    }));
    return;
  }

  // Cache-first strategy for everything else
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetch(event.request).then((response) => {
        // Don't cache non-success or non-GET
        if (!response || response.status !== 200 || event.request.method !== 'GET') {
          return response;
        }

        // Clone and cache
        const toCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, toCache);
        });

        return response;
      }).catch(() => {
        // Offline fallback for HTML pages
        if (event.request.headers.get('accept')?.includes('text/html')) {
          return caches.match('./index.html');
        }
      });
    })
  );
});
