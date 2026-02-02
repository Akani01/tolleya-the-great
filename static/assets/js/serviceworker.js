// Service Worker for Tolleya The Great
const CACHE_NAME = 'tolleya-v1.0';
const APP_PREFIX = 'tolleya_';
const VERSION = 'v1.0';
const CACHE_LIST = `${APP_PREFIX}${VERSION}`;

// Cache all assets from your structure - FIXED paths
const urlsToCache = [
    // Main page
    '/',
    
    // Important HTML pages
    '/school/',
    '/quiz/',
    
    // Static assets - use specific file paths instead of directories
    '/static/assets/css/style.css',
    '/static/assets/css/responsive.css',
    '/static/assets/css/nav.css',
    
    // Main JS files
    '/static/assets/js/main.js',
    '/static/assets/js/nav.js',
    
    // Fonts
    '/static/assets/fonts/',
    
    // Images
    '/static/assets/images/logo.png',
    '/static/assets/mediafiles/img/course-06.jpg',
    
    // Vendor scripts
    '/static/assets/js/vendor/jquery-3.2.1.min.js',
    '/static/assets/js/popper.min.js',
    '/static/assets/js/bootstrap.min.js',
    '/static/assets/js/plugins.js'
];

// Install Service Worker - FIXED version
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_LIST)
            .then(cache => {
                console.log('[Service Worker] Caching app shell');
                // Filter out directory URLs and only cache actual files
                const filesToCache = urlsToCache.filter(url => !url.endsWith('/'));
                return cache.addAll(filesToCache);
            })
            .then(() => {
                console.log('[Service Worker] Skip waiting on install');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('[Service Worker] Cache addAll failed:', error);
            })
    );
});

// Activate and clean old caches - FIXED version
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys().then(keyList => {
            return Promise.all(
                keyList.map(key => {
                    if (key !== CACHE_LIST && key.startsWith(APP_PREFIX)) {
                        console.log('[Service Worker] Removing old cache:', key);
                        return caches.delete(key);
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

// Fetch event with different strategies - FIXED version
self.addEventListener('fetch', event => {
    // Skip non-GET requests and browser extensions
    if (event.request.method !== 'GET') return;
    if (event.request.url.startsWith('chrome-extension://')) return;
    if (event.request.url.includes('extension')) return;
    
    const requestUrl = new URL(event.request.url);
    
    // Skip Google Ads and Analytics
    if (requestUrl.hostname.includes('googlesyndication.com') || 
        requestUrl.hostname.includes('google-analytics.com') ||
        requestUrl.hostname.includes('doubleclick.net')) {
        return;
    }
    
    // For static assets (CSS, JS, images, fonts)
    if (requestUrl.pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/i)) {
        event.respondWith(cacheFirstStrategy(event));
        return;
    }
    
    // For HTML pages
    if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(networkFirstStrategy(event));
        return;
    }
    
    // Default: try cache, then network
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response
                        const responseToCache = response.clone();
                        
                        caches.open(CACHE_LIST)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(() => {
                        // Return offline page for navigation requests
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline.html');
                        }
                        return new Response('You are offline');
                    });
            })
    );
});

// Cache First strategy for static assets - FIXED
async function cacheFirstStrategy(event) {
    const cachedResponse = await caches.match(event.request);
    if (cachedResponse) {
        // Update cache in background
        event.waitUntil(updateCache(event.request));
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(event.request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_LIST);
            await cache.put(event.request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Return a fallback for images
        if (event.request.url.match(/\.(png|jpg|jpeg|gif|svg)$/i)) {
            return caches.match('/static/assets/images/logo.png');
        }
        return new Response('Network error', { status: 408 });
    }
}

// Network First strategy for dynamic content - FIXED
async function networkFirstStrategy(event) {
    try {
        const networkResponse = await fetch(event.request);
        
        // Cache successful GET requests
        if (networkResponse.ok && event.request.method === 'GET') {
            const cache = await caches.open(CACHE_LIST);
            cache.put(event.request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Network failed, try cache
        const cachedResponse = await caches.match(event.request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return cached homepage for navigation requests
        if (event.request.mode === 'navigate') {
            return caches.match('/');
        }
        
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>You're Offline - Tolleya</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    h1 { color: #667eea; }
                    .btn { background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
                </style>
            </head>
            <body>
                <h1>You're Offline</h1>
                <p>Please check your internet connection and try again.</p>
                <a href="/" class="btn">Go to Homepage</a>
            </body>
            </html>
        `, {
            headers: { 'Content-Type': 'text/html' }
        });
    }
}

// Update cache in background - FIXED
async function updateCache(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_LIST);
            await cache.put(request, response);
        }
    } catch (error) {
        // Fail silently - it's okay if background update fails
    }
}

// Background sync - SIMPLIFIED for now
self.addEventListener('sync', event => {
    console.log('[Service Worker] Background sync:', event.tag);
    
    if (event.tag === 'sync-data') {
        event.waitUntil(syncPendingData());
    }
});

async function syncPendingData() {
    try {
        // Check if there's any pending data in IndexedDB
        const pendingData = await getPendingData();
        
        for (const data of pendingData) {
            try {
                const response = await fetch(data.url, {
                    method: data.method || 'POST',
                    headers: data.headers || {},
                    body: JSON.stringify(data.body)
                });
                
                if (response.ok) {
                    await removePendingData(data.id);
                }
            } catch (error) {
                console.error('Sync failed for:', data.id, error);
            }
        }
    } catch (error) {
        console.error('Sync process error:', error);
    }
}

// Simple IndexedDB helper functions
async function getPendingData() {
    return new Promise((resolve) => {
        const request = indexedDB.open('tolleya_sync', 1);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pending')) {
                db.createObjectStore('pending', { keyPath: 'id' });
            }
        };
        
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['pending'], 'readonly');
            const store = transaction.objectStore('pending');
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => {
                resolve(getAllRequest.result);
            };
            
            getAllRequest.onerror = () => {
                resolve([]);
            };
        };
        
        request.onerror = () => {
            resolve([]);
        };
    });
}

async function removePendingData(id) {
    return new Promise((resolve) => {
        const request = indexedDB.open('tolleya_sync', 1);
        
        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['pending'], 'readwrite');
            const store = transaction.objectStore('pending');
            store.delete(id);
            resolve();
        };
        
        request.onerror = () => {
            resolve();
        };
    });
}

// Push notifications - FIXED
self.addEventListener('push', event => {
    console.log('[Service Worker] Push received');
    
    let data = {
        title: 'Tolleya The Great',
        body: 'You have new educational updates!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        url: '/'
    };
    
    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (error) {
            console.error('Error parsing push data:', error);
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon || '/static/icons/icon-192x192.png',
        badge: data.badge || '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/',
            timestamp: Date.now()
        },
        actions: [
            {
                action: 'view',
                title: 'View Now',
                icon: '/static/icons/eye-72x72.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/icons/close-72x72.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click handler - FIXED
self.addEventListener('notificationclick', event => {
    console.log('[Service Worker] Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view' || !event.action) {
        // Default action - open the URL
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
    // For dismiss action, just close the notification (already done)
});

// Periodic sync for updates (if browser supports it)
if ('periodicSync' in self.registration) {
    self.addEventListener('periodicsync', event => {
        if (event.tag === 'update-content') {
            event.waitUntil(updateCachedContent());
        }
    });
}

async function updateCachedContent() {
    console.log('[Service Worker] Periodic sync updating content');
    
    try {
        const cache = await caches.open(CACHE_LIST);
        const requests = await cache.keys();
        
        for (const request of requests) {
            if (request.url.includes('/api/')) {
                // Skip API calls in periodic sync
                continue;
            }
            
            try {
                const response = await fetch(request);
                if (response.ok) {
                    await cache.put(request, response);
                }
            } catch (error) {
                // Skip failed updates
            }
        }
    } catch (error) {
        console.error('Periodic sync error:', error);
    }
}

// Message handler for communication from web page
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'UPDATE_CACHE') {
        updateCachedContent();
    }
});

// Helper function to clear all caches (for development)
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    return Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
}