// sw.js — FIXED (auto update + cache bust)
const CACHE_NAME = "garden-v3"; // <-- увеличивай номер при любых изменениях
const ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./script.js",
  "./data.js",
  "./manifest.json",
  "https://img.icons8.com/fluency/192/potted-plant.png"
];

// 1) Install: кладём файлы в кэш и сразу активируем новую версию SW
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

// 2) Activate: удаляем старые кэши и забираем контроль над страницами
self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null))
      );
      await self.clients.claim();
    })()
  );
});

// 3) Fetch:
// - Для html: network-first (чтобы всегда тянуть свежий index)
// - Для остального: stale-while-revalidate (быстро из кэша, но обновляет в фоне)
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Только GET
  if (req.method !== "GET") return;

  // HTML: network-first
  if (req.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(req);
          const cache = await caches.open(CACHE_NAME);
          cache.put(req, fresh.clone());
          return fresh;
        } catch (e) {
          const cached = await caches.match(req);
          return cached || caches.match("./index.html");
        }
      })()
    );
    return;
  }

  // Остальное: stale-while-revalidate
  event.respondWith(
    (async () => {
      const cached = await caches.match(req);
      const fetchPromise = fetch(req)
        .then((fresh) => {
          // кэшируем только свой домен
          if (url.origin === location.origin) {
            caches.open(CACHE_NAME).then((cache) => cache.put(req, fresh.clone()));
          }
          return fresh;
        })
        .catch(() => null);

      return cached || (await fetchPromise) || cached;
    })()
  );
});
