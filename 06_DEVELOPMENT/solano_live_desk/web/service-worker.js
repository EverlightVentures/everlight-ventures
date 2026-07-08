// Offline resilience: cache the app shell + last-known data so the survival OS
// still opens and shows the last picture when the network dies.
const CACHE = "sld-v3";
const SHELL = ["/", "/app.js", "/style.css", "/vendor/hls.min.js", "/manifest.json", "/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // API: network-first, fall back to the last cached response when offline.
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(
      fetch(e.request)
        .then((r) => { const cp = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, cp)); return r; })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // App shell + map tiles + CDN libs: cache-first, then network (runtime cache
  // so recently-viewed map areas keep working offline).
  e.respondWith(
    caches.match(e.request).then((cached) =>
      cached ||
      fetch(e.request)
        .then((r) => {
          if (r.ok || r.type === "opaque") {
            const cp = r.clone();
            caches.open(CACHE).then((c) => c.put(e.request, cp));
          }
          return r;
        })
        .catch(() => cached)
    )
  );
});
