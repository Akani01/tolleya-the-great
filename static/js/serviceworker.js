// Service Worker for Tolleya
const CACHE_NAME = 'tolleya-v1.0';
const APP_PREFIX = 'tolleya_';
const VERSION = 'v1.0.0';
const CACHE_LIST = `${APP_PREFIX}${VERSION}`;

// Cache core assets
const CORE_ASSETS = [
    '/',
    '/static/images/logo.png',
    '/static/assets/style.css',
    '/static/assets/css/responsive.css',
    '/static/assets/css/nav.css',
    '/static/assets/js/main.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css',
    'https://fonts.googleapis.com/css?family=Poppins:200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i&display=swap'
];

// Install Service Worker
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_LIST)
            .then(cache => {
                console.log('[Service Worker] Caching core assets');
                return cache.addAll(CORE_ASSETS);
            })
            .then(() => {
                console.log('[Service Worker] Skip waiting');
                return self.skipWaiting();
            })
    );
});

// Activate Service Worker
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_LIST && cache.startsWith(APP_PREFIX)) {
                        console.log('[Service Worker] Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        })
        .then(() => {
            console.log('[Service Worker] Claiming clients');
            return self.clients.claim();
        })
    );
});

// Fetch Strategy
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);
    
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // For static assets (CSS, JS, images)
    if (requestUrl.pathname.includes('/static/') || 
        requestUrl.pathname.includes('/assets/') ||
        requestUrl.pathname.includes('.css') ||
        requestUrl.pathname.includes('.js') ||
        requestUrl.pathname.match(/\.(png|jpg|jpeg|gif|svg|ico)$/)) {
        event.respondWith(cacheFirst(event.request));
        return;
    }
    
    // For HTML pages
    if (event.request.headers.get('Accept').includes('text/html')) {
        event.respondWith(networkFirst(event.request));
        return;
    }
    
    // For external resources (CDN)
    if (requestUrl.hostname.includes('cdn.jsdelivr.net') ||
        requestUrl.hostname.includes('cdnjs.cloudflare.com') ||
        requestUrl.hostname.includes('fonts.googleapis.com')) {
        event.respondWith(cacheFirst(event.request));
        return;
    }
    
    // Default: network first
    event.respondWith(fetch(event.request));
});

// Cache First Strategy
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // Update cache in background
        updateCache(request);
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_LIST);
            await cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Return fallback for images
        if (request.url.match(/\.(png|jpg|jpeg|gif|svg)$/i)) {
            return new Response(
                '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">' +
                '<rect width="100" height="100" fill="#f0f0f0"/>' +
                '<text x="50" y="50" text-anchor="middle" dy=".3em" fill="#999" font-family="Arial">T</text>' +
                '</svg>',
                { headers: { 'Content-Type': 'image/svg+xml' } }
            );
        }
        
        return new Response('Network error', { status: 408 });
    }
}

// Network First Strategy
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_LIST);
            await cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/offline/');
        }
        
        return new Response('You are offline', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Update cache in background
async function updateCache(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_LIST);
            await cache.put(request, response);
        }
    } catch (error) {
        // Fail silently
    }
}

// Listen for messages from the page
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SYNC_DATA') {
        syncPendingData();
    }
});

// Sync pending data when online
async function syncPendingData() {
    // Implement your data sync logic here
    console.log('[Service Worker] Syncing pending data...');
}

// Push notifications for Tolleya
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {
        title: 'Tolleya',
        body: 'New educational content available!',
        icon: '/static/images/logo.png',
        badge: '/static/icons/badge.png',
        tag: 'tolleya-update'
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            badge: data.badge,
            tag: data.tag,
            data: {
                url: data.url || '/'
            },
            actions: [
                {
                    action: 'open',
                    title: 'Open'
                },
                {
                    action: 'close',
                    title: 'Close'
                }
            ]
        })
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
});