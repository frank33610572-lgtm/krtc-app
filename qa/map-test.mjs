// 好用地圖自動測試：在 GitHub Actions 用手機尺寸的 Chromium 跑一遍，回報錯誤並存截圖
import { chromium } from "playwright";
import fs from "fs";
const OUT = "qa-out"; fs.mkdirSync(OUT, { recursive: true });
const log = [], errs = [], seen = new Map();
const pushErr = m => { const k = m.slice(0, 160); seen.set(k, (seen.get(k) || 0) + 1); if (seen.get(k) === 1 && errs.length < 300) errs.push(m); };
const note = (k, v) => { log.push([k, v]); console.log(k, JSON.stringify(v)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
  geolocation: { latitude: 22.6142, longitude: 120.3041 }, permissions: ["geolocation"], timezoneId: "Asia/Taipei", locale: "zh-TW" });
const p = await ctx.newPage();
p.on("pageerror", e => pushErr("pageerror: " + e.message + " @ " + (e.stack || "").split("\n")[1]));
p.on("console", m => { if (m.type() === "error" || m.type() === "warning") pushErr(m.type() + ": " + m.text().slice(0, 300)); });
p.on("requestfailed", r => { if (!/google-analytics|fonts/.test(r.url())) pushErr("requestfailed: " + r.url().slice(0, 120) + " " + (r.failure() || {}).errorText); });
const shot = async n => p.screenshot({ path: `${OUT}/${n}.png` });
const save = () => fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ log, errs, counts: [...seen].sort((a, b) => b[1] - a[1]).slice(0, 15) }, null, 1));
const step = async (name, fn) => { save(); console.log("STEP", name, "counts", JSON.stringify([...seen].sort((a, b) => b[1] - a[1]).slice(0, 3))); try { const r = await fn(); note("OK " + name, r ?? ""); } catch (e) { note("FAIL " + name, e.message.slice(0, 400)); errs.push("step " + name + ": " + e.message.slice(0, 200)); } };
const tapMap = async lnglat => {
  const pt = await p.evaluate(ll => { const r = map.getContainer().getBoundingClientRect(), q = map.project(ll); return [r.left + q.x, r.top + q.y]; }, lnglat);
  await p.touchscreen.tap(pt[0], pt[1]);
};
await p.goto("http://localhost:8000/index.html", { waitUntil: "networkidle" });
await sleep(1500); await shot("01-home");
await step("open map", async () => {
  await p.locator("nav button", { hasText: "地圖" }).click();
  await p.waitForFunction(() => typeof map !== "undefined" && map && styleReady, null, { timeout: 30000 });
  await sleep(2500); await shot("02-map");
});
await step("poi on", async () => {
  await p.click("#poiBtn");
  await p.waitForFunction(() => poi.official && poi.items.size > 20000, null, { timeout: 30000 });
  await sleep(4000); await shot("03-poi");
  return await p.evaluate(() => ({ items: poi.items.size, chips: [...document.querySelectorAll(".poichip")].map(b => b.innerText.replace(/\s+/g, " ")), msg: $("locMsg").textContent }));
});
await step("closeup", async () => {
  await p.evaluate(() => { map.jumpTo({ center: [120.3045, 22.6215], zoom: 16.6 }); }); await sleep(2500); await shot("03b-closeup");
});
await step("pie clusters", async () => {
  await p.evaluate(() => { map.jumpTo({ center: [120.3075, 22.6237], zoom: 13 }); }); await sleep(3000); await shot("04-pies");
  return await p.evaluate(() => ({ pies: map.listImages().filter(i => i.startsWith("pie")).length, feats: map.queryRenderedFeatures({ layers: ["poi-pie"] }).length }));
});
await step("tap cluster", async () => {
  const f = await p.evaluate(() => { const fs = map.queryRenderedFeatures({ layers: ["poi-cluster"] }); return fs.length ? fs[Math.floor(fs.length / 2)].geometry.coordinates : null; });
  const z0 = await p.evaluate(() => map.getZoom()); await tapMap(f); await sleep(1500);
  return { z0, z1: await p.evaluate(() => map.getZoom()) };
});
for (const c of ["food", "tea", "cafe", "bar", "conv"]) await step("popup " + c, async () => {
  const ll = await p.evaluate(c => { map.jumpTo({ center: [120.3045, 22.6215], zoom: 16.2 }); return null; }, c); await sleep(1800);
  const f = await p.evaluate(c => { const fs = map.queryRenderedFeatures({ layers: ["poi-glyph", "poi"] }).filter(f => f.properties.c === c); return fs.length ? fs[0].geometry.coordinates : null; }, c);
  if (!f) return "none in view";
  await tapMap(f); await sleep(900);
  if (!(await p.$(".maplibregl-popup"))) {   // 點的地方被別的圖示或按鈕蓋住：改成直接開這間店
    await p.evaluate(c => { const it = [...poi.items.values()].find(i => i.c === c && map.getBounds().contains([i.lon, i.lat])); poiOpen(it); }, c); await sleep(700);
  }
  const pop = await p.evaluate(() => { const el = document.querySelector(".maplibregl-popup"); return el ? el.innerText.replace(/\s+/g, " ").slice(0, 160) : null; });
  if (!pop) throw new Error("no popup");
  if (c === "food" || c === "bar") await shot("05-popup-" + c);
  if (/NaN|undefined|null/.test(pop)) throw new Error("bad text: " + pop);
  await p.evaluate(() => { if (popup) popup.remove(); });
  return pop;
});
await step("fav star", async () => {
  const f = await p.evaluate(() => map.queryRenderedFeatures({ layers: ["poi-glyph", "poi"] })[0].geometry.coordinates);
  await tapMap(f); await sleep(700);
  await p.click(".pp-star"); await sleep(500);
  const n = await p.evaluate(() => Object.keys(poiFav).length);
  await p.evaluate(() => { if (popup) popup.remove(); });
  return { favs: n };
});
await step("list rows", async () => {
  return await p.evaluate(() => [...document.querySelectorAll("#poiRes > *")].slice(0, 6).map(r => r.innerText.replace(/\s+/g, " ").slice(0, 70)));
});
await step("search", async () => {
  await p.fill("#poiQ", "星巴克"); await p.press("#poiQ", "Enter"); await sleep(800); await shot("06-search");
  const r = await p.evaluate(() => [...document.querySelectorAll("#poiRes > *")].slice(0, 4).map(r => r.innerText.replace(/\s+/g, " ").slice(0, 70)));
  await p.click("#poiQx"); return r;
});
await step("from station", async () => {
  await p.click('.poisrc button[data-src="from"]'); await sleep(2500); await shot("07-from");
  return await p.evaluate(() => [...document.querySelectorAll("#poiRes > *")].slice(0, 4).map(r => r.innerText.replace(/\s+/g, " ").slice(0, 80)));
});
await step("fav tab", async () => {
  await p.click('.poisrc button[data-src="fav"]'); await sleep(800);
  const r = await p.evaluate(() => document.querySelector("#poiRes").innerText.slice(0, 120));
  await p.click('.poisrc button[data-src="here"]'); return r;
});
await step("long press solo", async () => {
  const el = p.locator('.poichip[data-cat="bar"]'); const bb = await el.boundingBox();
  await el.dispatchEvent("pointerdown"); await sleep(650); await el.dispatchEvent("pointerup"); await el.dispatchEvent("click"); await sleep(1200);
  await shot("08-solo-bar");
  const st = await p.evaluate(() => ({ cats: { ...poi.cats }, msg: $("locMsg").textContent }));
  await el.dispatchEvent("pointerdown"); await sleep(650); await el.dispatchEvent("pointerup"); await el.dispatchEvent("click"); await sleep(500);
  return { st, after: await p.evaluate(() => ({ ...poi.cats })) };
});
await step("hide closed + atm", async () => {
  await p.click("#poiHide"); await sleep(600); await p.click("#poiAtm"); await sleep(600);
  const r = await p.evaluate(() => ({ hide: poi.hideClosed, atm: poi.atm }));
  await p.click("#poiHide"); await p.click("#poiAtm"); return r;
});
await step("hours editor", async () => {
  await p.evaluate(() => { const it = [...poi.items.values()].find(i => !ohStatus(i).known && map.getBounds().contains([i.lon, i.lat])); poiOpen(it); }); await sleep(700);
  await p.click("[data-ohedit]"); await sleep(600); await shot("09-oh-editor");
  const open = await p.evaluate(() => $("ohDlg").open);
  await p.keyboard.press("Escape"); await p.evaluate(() => { if (popup) popup.remove(); });
  return { open };
});
await step("theme dark/light", async () => {
  for (const t of ["dark", "light"]) {
    await p.evaluate(t => { applyTheme(t); }, t);
    await p.waitForFunction(() => styleReady, null, { timeout: 20000 }); await sleep(2500);
    await p.evaluate(() => { map.jumpTo({ center: [120.3075, 22.6237], zoom: 13 }); }); await sleep(2000);
    await shot("10-theme-" + t);
    await p.evaluate(() => { map.jumpTo({ center: [120.3045, 22.6215], zoom: 16.6 }); }); await sleep(2200); await shot("10b-close-" + t);
  }
  const r = await p.evaluate(() => ({ layers: ["poi-pie", "poi-glyph", "poi-cluster"].map(l => !!map.getLayer(l)), feats: map.queryRenderedFeatures({ layers: ["poi-pie"] }).length }));
  await p.evaluate(() => { applyTheme("auto"); }); await p.waitForFunction(() => styleReady); return r;
});
await step("youbike", async () => {
  await p.click("#ybToggle"); await sleep(6000); await shot("11-youbike");
  return await p.evaluate(() => ({ yb: yb.on, poi: poi.on, msg: $("locMsg").textContent, n: (map.getSource("yb")?._data?.features || []).length }));
});
await step("locate", async () => {
  await p.click("#locate"); await sleep(4000); await shot("12-locate");
  return await p.evaluate(() => ({ msg: $("locMsg").textContent, list: (document.querySelector("#ybList, #nearList, .near") || {}).innerText?.slice(0, 160) }));
});
await step("back to list + board", async () => {
  await p.locator("nav button", { hasText: "班次" }).click(); await sleep(1500); await shot("13-list");
  return await p.evaluate(() => document.querySelector(".board")?.innerText.replace(/\s+/g, " ").slice(0, 160));
});
await step("settings", async () => {
  await p.locator("nav button", { hasText: "設定" }).click(); await sleep(1000); await shot("14-settings");
  return await p.evaluate(() => document.querySelector("#ttStatus")?.innerText);
});
const counts = [...seen].sort((a, b) => b[1] - a[1]).slice(0, 15);
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ log, errs, counts }, null, 1));
console.log("COUNTS", JSON.stringify(counts));
console.log("ERRORS", errs.length); errs.forEach(e => console.log(" -", e));
await b.close();
