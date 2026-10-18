const CACHE = "avalon-public-v5.5";
const PUBLIC = [
  "/static/app.css?v=5.5",
  "/static/app.js?v=5.5",
  "/static/core.js?v=5.5",
  "/static/presence.glsl?v=5.5",
  "/static/art/progre.png?v=5.5",
  ...["ethereal", "sentinel", "mascot", "abstract"].map(
    (name) => `/static/avatars/${name}.png`,
  ),
  "/static/constellation-core.js",
  "/static/galaxy.js",
  "/static/cairo-canvas.js",
  "/static/offline.html",
  "/static/icons/avalon-192.png",
  "/static/icons/avalon-512.png",
];
self.addEventListener("install", (event) =>
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PUBLIC))),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("avalon-public-") && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      ),
  ),
);
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin)
    return;
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/static/offline.html")),
    );
    return;
  }
  if (PUBLIC.includes(url.pathname + url.search))
    event.respondWith(
      caches.match(event.request).then((hit) => hit || fetch(event.request)),
    );
});
