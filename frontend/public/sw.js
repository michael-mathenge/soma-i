const CACHE = "somai-public-shell-v2";
const SHELL = ["/", "/manifest.webmanifest"];
self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const response = await fetch("/");
      const html = await response.text();
      const assets = [
        ...html.matchAll(/(?:src|href)="([^"]+\.(?:js|css))"/g),
      ].map((match) => match[1]);
      const cache = await caches.open(CACHE);
      await cache.addAll([...SHELL, ...assets]);
      await self.skipWaiting();
    })(),
  );
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/")));
  }
});
self.addEventListener("message", (event) => {
  if (event.data === "account-cache-version")
    event.ports[0]?.postMessage("public-shell-v2");
});
