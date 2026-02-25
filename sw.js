// sw.js (cache-safe, history.json always fresh)

const CACHE_NAME = "garden-v3";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./script.js",
  "./data.js",
  "./manifest.json",
  "./history.json",
  "https://img.icons8.com/fluency/192/potted-plant.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // 🔥 ВАЖНО: историю никогда не кэшируем (иначе "не появляются записи")
  if (url.pathname.endsWith("/history.json") || url.pathname.endsWith("history.json")) {
    e.respondWith(fetch(e.request, { cache: "no-store" }));
    return;
  }

  // cache-first for everything else
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});
