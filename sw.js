// 高捷班次：離線快取。改版時更新 CACHE 版本號（也寫進 version.json），App 會自動換新版。
const CACHE = "krtc-2026-11-21-v73";
const TILE_CACHE = "krtc-tiles-v2";
const LIB_CACHE = "krtc-lib-v1";    // 地圖程式庫、字型：網址本身帶版本，改版不用重下載
const DATA_CACHE = "krtc-data-v1";  // 店家等資料：先給快取、背景更新，改版不用重下載 2 MB
const KEEP = [CACHE, TILE_CACHE, LIB_CACHE, DATA_CACHE];
const ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"];
const LIBS = ["https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"];
const DATA = ["./stores.json"];

// 已經有的就不再下載
async function fillMissing(name, urls) {
  const c = await caches.open(name);
  await Promise.all(urls.map(async u => { if (!(await c.match(u))) { const r = await fetch(new Request(u, {cache: "reload"})); if (r.ok) await c.put(u, r); } }));
}
self.addEventListener("install", e => {
  // cache: "reload" 繞過瀏覽器的 HTTP 快取（GitHub Pages 會叫手機留 10 分鐘），確保存到的是新版
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS.map(u => new Request(u, {cache: "reload"}))))
    .then(() => Promise.all([fillMissing(LIB_CACHE, LIBS), fillMissing(DATA_CACHE, DATA)]).catch(() => {}))
    .then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => !KEEP.includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
// 圖磚快取上限：每存 80 張才整理一次（原本每張都整理，平移地圖時會拖慢載入）
let tilePuts = 0, trimming = false;
async function trimTiles(max) {
  if (trimming) return; trimming = true;
  try { const c = await caches.open(TILE_CACHE), keys = await c.keys(); await Promise.all(keys.slice(0, Math.max(0, keys.length - max)).map(k => c.delete(k))); }
  finally { trimming = false; }
}
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // 頁面：有網路時拿最新版，沒網路時用快取
  if (req.mode === "navigate") {
    e.respondWith(fetch(req.url, {cache: "no-cache", credentials: "same-origin"}).then(r => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put("./index.html", copy)); } return r; })
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
        if (r.ok) { c.put(req, r.clone()); if (++tilePuts % 80 === 0) e.waitUntil(trimTiles(1500)); }
        return r;
      } catch (err) { if (hit) return hit; throw err; }
    }));
    return;
  }
  // 字型與程式庫：先用快取
  if (url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com") || url.hostname === "cdnjs.cloudflare.com") {
    e.respondWith(caches.open(LIB_CACHE).then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const r = await fetch(req); if (r.ok) c.put(req, r.clone()); return r;
    }));
    return;
  }
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith("/version.json")) return; // 版本檢查一律走網路
  // 店家資料、頁面附件：先給快取，背景再更新
  const name = url.pathname.endsWith(".json") ? DATA_CACHE : CACHE;
  e.respondWith(caches.open(name).then(async c => {
    const hit = await c.match(req, {ignoreSearch: true}) || (name === DATA_CACHE ? null : await caches.match(req, {ignoreSearch: true}));
    const net = fetch(req.url, {cache: "no-cache"}).then(r => { if (r.ok) c.put(url.pathname.endsWith("/") ? "./" : req.url.split("?")[0], r.clone()); return r; });
    if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
    return net;
  }));
});
