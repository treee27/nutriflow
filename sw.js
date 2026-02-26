// ── NutriFlow Service Worker ─────────────────────────────────────
const CACHE_NAME = 'nutriflow-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// ── Install: cache all static assets ─────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching app shell');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch: serve from cache, fallback to network ─────────────────
self.addEventListener('fetch', (event) => {
  // Skip non-GET and API requests (always fetch live from backend)
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/suggest')) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((response) => {
        // Cache new assets dynamically
        if (response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    }).catch(() => {
      // Offline fallback — serve cached index.html
      return caches.match('/index.html');
    })
  );
});

// ── Push Notifications (meal reminders) ──────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const options = {
    body: data.body || 'Time to log your meal! 🌿',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    vibrate: [200, 100, 200],
    tag: 'meal-reminder',
    renotify: true,
    actions: [
      { action: 'open', title: '🍽️ Log Meal' },
      { action: 'dismiss', title: 'Later' }
    ],
    data: { url: '/' }
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'NutriFlow Reminder', options)
  );
});

// ── Notification click: open the app ─────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === '/' && 'focus' in client) return client.focus();
      }
      return clients.openWindow('/');
    })
  );
});