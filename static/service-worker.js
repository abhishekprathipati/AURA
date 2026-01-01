// AURA Service Worker - Offline Support for Relaxation Features
const CACHE_NAME = 'aura-offline-v1';
const OFFLINE_URLS = [
    '/student/relax',
    '/static/css/global.css',
    '/static/css/style.css',
    '/static/js/theme.js',
    '/static/js/main.js',
    '/static/js/mood_handler.js'
];

// Install event - cache critical resources
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching offline pages');
                return cache.addAll(OFFLINE_URLS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
    // Only handle GET requests
    if (event.request.method !== 'GET') return;
    
    // Only cache navigation and static resources
    if (event.request.mode === 'navigate' || 
        event.request.destination === 'style' ||
        event.request.destination === 'script') {
        
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    // Clone response and cache it
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                    return response;
                })
                .catch(() => {
                    // Network failed, try cache
                    return caches.match(event.request)
                        .then((cachedResponse) => {
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // Return offline page
                            return caches.match('/student/relax');
                        });
                })
        );
    }
});

// Message event - allow clients to communicate with service worker
self.addEventListener('message', (event) => {
    if (event.data.action === 'skipWaiting') {
        self.skipWaiting();
    }
});
