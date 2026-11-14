// 高捷班次：離線快取。改版時更新 CACHE 版本號，手機下次打開就會換新版。
const CACHE = "krtc-2026-11-14-v23";
const TILE_CACHE = "krtc-tiles-v2";
const ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png", "./stores.json",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== TILE_CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
async function trim(name, max) {
  const c = await caches.open(name), keys = await c.keys();
  for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
}
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // 頁面：有網路時拿最新版，沒網路時用快取
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put("./index.html", copy)); return r; })
      .catch(() => caches.match("./index.html")));
    return;
  }
  // 地圖：樣式與字型先用網路、沒網路用快取；圖磚看過的區域離線也能顯示
  if (url.hostname === "tiles.openfreemap.org") {
    e.respondWith(caches.open(TILE_CACHE).then(async c => {
      const hit = await c.match(req);
      const isTile = /\.(pbf|png)$/.test(url.pathname) && !url.pathname.startsWith("/styles");
      if (hit && isTile) return hit;
      try {
        const r = await fetch(req);
        if (r.ok) { c.put(req, r.clone()); trim(TILE_CACHE, 1500); }
        return r;
      } catch (err) { if (hit) return hit; throw err; }
    }));
    return;
  }
  // 字型與程式庫：先用快取
  if (url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com") || url.hostname === "cdnjs.cloudflare.com") {
    e.respondWith(caches.open(CACHE).then(async c => {
      const hit = await c.match(req);
      const net = fetch(req).then(r => { c.put(req, r.clone()); return r; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }
  if (url.origin !== location.origin) return;
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(hit => hit || fetch(req)));
});
