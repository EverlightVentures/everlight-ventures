const CACHE = "aa-dashboard-v1";
const ASSETS = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/static")) {
    event.respondWith(caches.match(event.request).then((r) => r || fetch(event.request)));
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match("/")));
});
