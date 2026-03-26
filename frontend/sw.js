const CACHE_NAME = 'nurser-v1';
const STATIC_ASSETS = [
  '/contributor.html',
  '/admin.html',
  '/login.html',
  '/nurser.css',
  '/logo_192.png',
  '/logo_512.png',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;
  // Don't cache API calls
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/auth') || url.pathname.startsWith('/teams') ||
      url.pathname.startsWith('/events') || url.pathname.startsWith('/users')) return;

  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});

// Push notification handler
self.addEventListener('push', event => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'Nurser', {
      body: data.body || '',
      icon: '/logo_192.png',
      badge: '/logo_192.png',
      data: data.url || '/'
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      if (clientList.length > 0) return clientList[0].focus();
      return clients.openWindow(event.notification.data || '/');
    })
  );
});
