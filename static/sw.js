const CACHE = "security-maintenance-v1";
const API_BASE = "";

self.addEventListener("install", (e) => {
    self.skipWaiting();
    e.waitUntil(
        caches.open(CACHE).then((c) => c.addAll([
            "/",
            "/static/css/style.css",
            "/static/js/app.js",
            "/static/manifest.json"
        ]))
    );
});

self.addEventListener("activate", (e) => {
    e.waitUntil(clients.claim());
});

self.addEventListener("fetch", (e) => {
    // Only cache static assets, not API calls
    if (e.request.url.includes("/api/")) return;
    e.respondWith(
        caches.match(e.request).then((r) => r || fetch(e.request))
    );
});
