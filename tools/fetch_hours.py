"""每月更新營業時間來源（GitHub Actions 執行）。

- data/osm_hours.txt   ：OpenStreetMap 全高雄有填營業時間的超商、手搖飲、咖啡廳
- data/chain_hours2.txt：迷客夏、cama 官網的高雄門市營業時間
星巴克（data/chain_hours.txt）的門市座標要在瀏覽器裡才拿得到，維持手動更新。
任何一個來源抓失敗就保留舊檔，不會把資料清掉。
"""
import html, json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "krtc-app hours refresh (+https://frank33610572-lgtm.github.io/krtc-app/)"}


def get(url, data=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"[\t\n\r]", " ", str(s or "")).strip()


def osm():
    bbox = "22.45,120.15,22.92,120.52"
    q = (f'[out:json][timeout:180];(nwr["amenity"="cafe"]({bbox});'
         f'nwr["shop"~"^(bubble_tea|tea|beverages|convenience)$"]({bbox});'
         f'nwr["cuisine"~"bubble_tea|tea|coffee|juice"]({bbox}););out center tags;')
    for host in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        try:
            j = json.loads(get(host, ("data=" + urllib.parse.quote(q)).encode(), timeout=240))
            break
        except Exception as e:
            print("overpass failed", host, e)
    else:
        return None
    out = []
    for e in j["elements"]:
        t = e.get("tags", {})
        if not t.get("opening_hours"): continue
        k = "c" if t.get("shop") == "convenience" else "f" if t.get("amenity") == "cafe" and not re.search(r"bubble_tea|tea|juice", t.get("cuisine", "")) else "t"
        lat = e.get("lat", e.get("center", {}).get("lat")); lon = e.get("lon", e.get("center", {}).get("lon"))
        if lat is None: continue
        out.append("\t".join([k, e["type"][0] + str(e["id"]), clean(t.get("name")), clean(t.get("brand")), clean(t.get("branch")),
                              f"{lat:.6f}", f"{lon:.6f}", clean(t["opening_hours"])]))
    return out


def milksha():
    h = get("https://www.milksha.com/store_detail.php?uID=1")
    out = []
    for block in re.findall(r"<a[^>]*>(.*?)</a>", h, re.S):
        n = re.search(r"<h3>(.*?)</h3>", block, re.S); a = re.search(r"<p>(.*?)</p>", block, re.S)
        if not (n and a): continue
        name = html.unescape(re.sub(r"<[^>]+>", "", n.group(1))).strip()
        addr = re.sub(r"^\d{3,6}", "", html.unescape(re.sub(r"<[^>]+>", "", a.group(1))).strip())
        if "高雄" not in addr: continue
        lis = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<li>(.*?)</li>", block, re.S)]
        hrs = " ".join(x for x in lis if re.search(r"\d{1,2}:\d{2}|公休|休", x))
        name = re.sub(r"❄️|Milksha Plus\s*", "", name).strip()
        out.append("|".join(["MS", "迷客夏 " + name, "", "", hrs, addr]))
    return out


def cama():
    h = get("https://www.camacafe.com/store")
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    h = re.sub(r"<br\s*/?>|</(p|div|li|h\d|tr|td|span)>", "\n", h)
    lines = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in h.split("\n")]
    lines = [x for x in lines if x]
    stores, cur = [], None
    for l in lines:
        if re.search(r"門市[\d.]*\s*-\s*\S+店", l) or l.startswith("旗艦門市-"):
            if cur: stores.append(cur)
            cur = {"name": re.sub(r"^.*?-\s*", "", l), "lines": []}
        elif cur:
            cur["lines"].append(l)
    if cur: stores.append(cur)
    out = []
    for st in stores:
        if not st["lines"] or "高雄" not in st["lines"][0]: continue
        hrs = " ".join([x for x in st["lines"][1:] if re.search(r"\d{1,2}[:：]\d{2}|店休|公休", x)][:3])
        out.append("|".join(["CA", "cama " + st["name"], "", "", hrs, st["lines"][0]]))
    return out


def save(path, rows, minimum):
    if rows is None or len(rows) < minimum:
        print(f"keep old {path}: got {0 if rows is None else len(rows)} rows (< {minimum})"); return
    open(path, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print(f"wrote {path}: {len(rows)} rows")


if __name__ == "__main__":
    try: save("data/osm_hours.txt", osm(), 500)
    except Exception as e: print("osm error", e)
    chain = []
    for name, fn, need in (("milksha", milksha, 20), ("cama", cama, 3)):
        try:
            rows = fn(); print(name, len(rows))
            if len(rows) >= need: chain += rows
            else: raise RuntimeError("too few")
        except Exception as e:
            print(name, "error", e)
            old = [l for l in open("data/chain_hours2.txt", encoding="utf-8").read().splitlines() if l.startswith({"milksha": "MS|", "cama": "CA|"}[name])]
            chain += old; print(name, "kept old", len(old))
    save("data/chain_hours2.txt", chain, 10)
