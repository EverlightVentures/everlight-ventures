/* ALLEY KINGZ -- KILL-SWITCH SERVICE WORKER (2026-06-20)
   A previous build registered a caching service worker that pins the OLD app
   in players' browsers (so deploys never appear even on refresh). This file
   REPLACES it: on activate it clears every cache, unregisters itself, and
   reloads open tabs -> the browser falls back to the live network build.
   AK no longer ships a caching SW; this is a one-way eviction. */
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil((async function () {
    try {
      var keys = await caches.keys();
      await Promise.all(keys.map(function (k) { return caches.delete(k); }));
    } catch (_) {}
    try { await self.registration.unregister(); } catch (_) {}
    try {
      var cs = await self.clients.matchAll({ type: 'window' });
      cs.forEach(function (c) { try { c.navigate(c.url); } catch (_) {} });
    } catch (_) {}
  })());
});
/* never serve from cache -- always go to network (belt + suspenders while the SW lingers) */
self.addEventListener('fetch', function (e) { return; });
