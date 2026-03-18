// AURA Service Worker - Offline Support with Intelligent Caching Strategies
// Version: v5 (cache-first for static, network-first for dynamic)

const CACHE_NAME = 'aura-offline-v5';
const STATIC_CACHE_NAME = 'aura-static-v5';

// Critical resources to pre-cache during installation
const PRECACHE_URLS = [
    '/student/relax',
    '/static/css/global.css',
    '/static/css/style.css',
    '/static/js/theme-engine.js',
    '/static/js/main.js',
    '/static/js/mood_handler.js'
];

// Static asset patterns - use cache-first strategy
// These files have fingerprinted names or rarely change
const STATIC_ASSET_PATTERNS = [
    /^\/static\/css\//,
    /^\/static\/js\//,
    /^\/static\/images\//,
    /^\/static\/fonts\//,
    /\.(?:css|js|woff2?|ttf|eot|svg|png|jpg|jpeg|gif|ico|webp)$/i
];

// Dynamic content patterns - use network-first strategy
// API calls, HTML pages, and user-specific content
const NETWORK_FIRST_PATTERNS = [
    /^\/api\//,
    /^\/student\//,
    /^\/proctor\//,
    /^\/parent\//,
    /^\/health$/
];

/**
 * Check if a URL matches any pattern in the given list
 */
function matchesPattern(url, patterns) {
    const pathname = new URL(url).pathname;
    return patterns.some(pattern => pattern.test(pathname));
}

/**
 * Determine caching strategy based on request type
 */
function getCacheStrategy(request) {
    const url = request.url;

    // API calls should never be cached
    if (matchesPattern(url, [/^\/api\//])) {
        return 'network-only';
    }

    // Static assets use cache-first (faster, offline-capable)
    if (matchesPattern(url, STATIC_ASSET_PATTERNS)) {
        return 'cache-first';
    }

    // HTML pages and navigation use network-first (always fresh when online)
    if (request.mode === 'navigate' || matchesPattern(url, NETWORK_FIRST_PATTERNS)) {
        return 'network-first';
    }

    // Default to network-first for everything else
    return 'network-first';
}

// Install event - pre-cache critical resources
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing v5...');
    event.waitUntil(
        Promise.all([
            // Pre-cache critical resources
            caches.open(CACHE_NAME).then((cache) => {
                console.log('[Service Worker] Pre-caching critical resources');
                return cache.addAll(PRECACHE_URLS);
            }),
            // Initialize static cache
            caches.open(STATIC_CACHE_NAME)
        ]).then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating v5...');
    const currentCaches = [CACHE_NAME, STATIC_CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => !currentCaches.includes(name))
                    .map((name) => {
                        console.log('[Service Worker] Deleting old cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - intelligent caching strategies
self.addEventListener('fetch', (event) => {
    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    const strategy = getCacheStrategy(event.request);

    switch (strategy) {
        case 'cache-first':
            event.respondWith(cacheFirstStrategy(event.request));
            break;
        case 'network-first':
            event.respondWith(networkFirstStrategy(event.request));
            break;
        case 'network-only':
            // Let the request pass through without caching
            return;
        default:
            event.respondWith(networkFirstStrategy(event.request));
    }
});

/**
 * Cache-First Strategy
 * Best for static assets (CSS, JS, images, fonts)
 * Returns cached version immediately, updates cache in background
 */
async function cacheFirstStrategy(request) {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
        // Return cached response immediately
        // Optionally update cache in background (stale-while-revalidate)
        updateCacheInBackground(request, cache);
        return cachedResponse;
    }

    // Not in cache, fetch from network
    try {
        const networkResponse = await fetch(request);
        // Cache the response for future use
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('[Service Worker] Cache-first fetch failed:', error);
        // Return a basic offline response for static assets
        return new Response('/* Offline - resource unavailable */', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

/**
 * Network-First Strategy
 * Best for dynamic content (HTML pages, API calls)
 * Tries network first, falls back to cache
 */
async function networkFirstStrategy(request) {
    const cache = await caches.open(CACHE_NAME);

    try {
        const networkResponse = await fetch(request);
        // Cache successful responses
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Network failed, try cache
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            console.log('[Service Worker] Serving from cache:', request.url);
            return cachedResponse;
        }

        // For navigation requests, return offline page
        if (request.mode === 'navigate') {
            const offlinePage = await cache.match('/student/relax');
            if (offlinePage) {
                return offlinePage;
            }
        }

        // Return generic offline response
        return new Response('Offline - Please check your connection', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

/**
 * Background cache update (stale-while-revalidate pattern)
 * Updates cache without blocking the response
 */
function updateCacheInBackground(request, cache) {
    fetch(request).then((networkResponse) => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse);
        }
    }).catch(() => {
        // Silently fail - we already served cached version
    });
}

// Message event - allow clients to communicate with service worker
self.addEventListener('message', (event) => {
    if (event.data.action === 'skipWaiting') {
        self.skipWaiting();
    }

    // Allow manual cache clearing
    if (event.data.action === 'clearCache') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((name) => caches.delete(name))
                );
            }).then(() => {
                console.log('[Service Worker] All caches cleared');
            })
        );
    }
});
