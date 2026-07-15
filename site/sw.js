/**
 * Akamonkai Japanese — Service Worker
 *
 * Strategy:
 *  - Install is FAST (core shell only) and activates immediately, so clients
 *    never linger on a stale version behind a huge precache download.
 *  - Pages/data (HTML/JSON/JS/CSS) are network-first with cache fallback:
 *    always fresh when online, still available offline.
 *  - Media (audio/images/video/pdf) is cache-first in a STABLE cache that
 *    survives deploys, so updates don't re-download the whole course.
 *  - The full offline precache runs in the background when the page sends
 *    {type:'PRECACHE_ALL'} (see app.js), never blocking updates.
 */

const BUILD_ID = '20260715055144';
const SHELL_CACHE = `akamonkai-shell-${BUILD_ID}`;
const MEDIA_CACHE = 'akamonkai-media-v2';

const CORE_URLS = [
  './',
  './index.html',
  './worksheets.html',
  './css/style.css',
  './js/app.js',
  './lesson-data.json',
  './manifest.json',
];

const MEDIA_RE = /\.(m4a|mp3|wav|ogg|jpg|jpeg|png|gif|webp|svg|mp4|webm|pdf|ico|woff2?)$/i;

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(CORE_URLS)).catch(() => {})
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => Promise.all(
      names
        .filter((n) => n !== SHELL_CACHE && n !== MEDIA_CACHE)
        .map((n) => caches.delete(n))
    )).then(() => self.clients.claim())
  );
});

// Background full precache, triggered by the page after load.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'PRECACHE_ALL') {
    event.waitUntil(precacheAll());
  }
});

async function precacheAll() {
  try {
    const resp = await fetch('./precache-manifest.json', { cache: 'no-store' });
    if (!resp.ok) return;
    const payload = await resp.json();
    const urls = Array.isArray(payload.urls) ? payload.urls.filter(Boolean) : [];
    const media = await caches.open(MEDIA_CACHE);
    const shell = await caches.open(SHELL_CACHE);
    for (const url of urls) {
      const target = MEDIA_RE.test(url.split('?')[0]) ? media : shell;
      if (await target.match(url)) continue;
      try { await target.add(url); } catch { /* skip individual failures */ }
    }
  } catch { /* offline or aborted — retried on a later visit */ }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;

  // Never intercept cross-origin or API traffic.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request).catch(() =>
      new Response('{"error":"offline"}', { headers: { 'Content-Type': 'application/json' } })
    ));
    return;
  }

  const isMedia = MEDIA_RE.test(url.pathname);

  if (isMedia) {
    // Cache-first: media files are content-addressed enough (renames on change).
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request).then((resp) => {
        if (resp && resp.status === 200) {
          const copy = resp.clone();
          caches.open(MEDIA_CACHE).then((c) => c.put(event.request, copy));
        }
        return resp;
      }))
    );
    return;
  }

  // Network-first for pages/data: always current when online, cached for offline.
  event.respondWith(
    fetch(event.request).then((resp) => {
      if (resp && resp.status === 200) {
        const copy = resp.clone();
        caches.open(SHELL_CACHE).then((c) => c.put(event.request, copy));
      }
      return resp;
    }).catch(() =>
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        if (event.request.headers.get('accept')?.includes('text/html')) {
          return caches.match('./index.html');
        }
      })
    )
  );
});
