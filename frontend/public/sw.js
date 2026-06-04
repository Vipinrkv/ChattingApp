const CACHE_VERSION = "chattingapp-v2026-06-01";
const APP_SHELL_CACHE = `${CACHE_VERSION}-shell`;
const API_CACHE = `${CACHE_VERSION}-api`;
const APP_SHELL = [
  "/",
  "/index.html",
  "/offline.html",
  "/manifest.webmanifest",
  "/favicon.ico.svg",
];
const API_CACHE_PATTERNS = [
  "/api/v1/users/me",
  "/api/v1/posts",
  "/api/v1/groups",
  "/api/v1/friends",
  "/api/v1/chats",
  "/api/v1/messages",
  "/api/v1/notifications",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(APP_SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !key.startsWith(CACHE_VERSION))
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("sync", (event) => {
  if (event.tag === "chattingapp-background-sync") {
    event.waitUntil(notifyClients({ type: "BACKGROUND_SYNC_READY" }));
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (url.origin === self.location.origin && isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request, APP_SHELL_CACHE));
    return;
  }

  if (shouldCacheApi(url)) {
    event.respondWith(networkFirst(request, API_CACHE));
  }
});

function isStaticAsset(pathname) {
  return (
    pathname.startsWith("/assets/") ||
    APP_SHELL.includes(pathname) ||
    pathname.match(/\.(js|css|svg|png|jpg|jpeg|webmanifest|ico)$/)
  );
}

function shouldCacheApi(url) {
  return API_CACHE_PATTERNS.some((pattern) => url.pathname.startsWith(pattern));
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error("Offline and no cached response available");
  }
}

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(APP_SHELL_CACHE);
    cache.put("/index.html", response.clone());
    return response;
  } catch {
    return (await caches.match("/index.html")) || caches.match("/offline.html");
  }
}

async function notifyClients(message) {
  const clients = await self.clients.matchAll({
    includeUncontrolled: true,
    type: "window",
  });
  await Promise.all(clients.map((client) => client.postMessage(message)));
}
