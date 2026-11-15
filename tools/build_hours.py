"""Merge opening hours (OSM + Starbucks official) into krtc-app/stores.json.

shop rows become [name, addr, cafe, a, o, oh, display]; fam rows get oh at [5]; hl rows get oh at [6].
Unmatched tea/cafe shops that have hours are added as new shop rows.
"""
import json, math, re, sys

stores_path, osm_path, chain_path = sys.argv[1:4]
chain_paths = [chain_path] + sys.argv[4:]
S = json.load(open(stores_path))
ll = lambda a, o: ((a + 2200000) / 1e5, (o + 12000000) / 1e5)
off = lambda lat, lon: [round(lat * 1e5) - 2200000, round(lon * 1e5) - 12000000]

def dist(p, q):
    dy = (p[0] - q[0]) * 111320
    dx = (p[1] - q[1]) * 111320 * math.cos(math.radians(22.65))
    return math.hypot(dx, dy)

class Grid:
    def __init__(self, pts, cell=0.001):
        self.c, self.g = cell, {}
        for i, p in enumerate(pts):
            self.g.setdefault((int(p[0] / cell), int(p[1] / cell)), []).append(i)
        self.pts = pts
    def near(self, p, r):
        ci, cj, out = int(p[0] / self.c), int(p[1] / self.c), []
        for i in range(ci - 1, ci + 2):
            for j in range(cj - 1, cj + 2):
                for k in self.g.get((i, j), []):
                    d = dist(p, self.pts[k])
                    if d <= r: out.append((d, k))
        return sorted(out)

OHD = r"(?:Mo|Tu|We|Th|Fr|Sa|Su)"
RULE = re.compile(rf"^(?:{OHD}(?:-{OHD})?(?:,{OHD}(?:-{OHD})?)*\s+)?(?:off|closed|24/7|\d{{1,2}}:\d{{2}}\s*-\s*\d{{1,2}}:\d{{2}}\+?(?:\s*,\s*\d{{1,2}}:\d{{2}}\s*-\s*\d{{1,2}}:\d{{2}}\+?)*)$")
def valid_oh(s):
    s = s.strip()
    if not s: return False
    rules = [r.strip() for r in s.split(";") if r.strip() and not re.match(r"^(PH|SH)\b", r.strip())]
    return bool(rules) and all(RULE.match(r) for r in rules)

# ---- OSM
osm = []
for line in open(osm_path, encoding="utf-8"):
    k, oid, name, brand, branch, lat, lon, oh = line.rstrip("\n").split("\t")
    oh = oh.strip()
    if not valid_oh(oh): continue
    osm.append(dict(k=k, name=name, brand=brand, branch=branch, p=(float(lat), float(lon)), oh=oh))

# ---- Starbucks official: "(一~五)07:30~19:30 (六~日)不營業" -> "Mo-Fr 07:30-19:30; Sa-Su off"
DAY = {"一": "Mo", "二": "Tu", "三": "We", "四": "Th", "五": "Fr", "六": "Sa", "日": "Su"}
def sb_oh(t):
    t = t.replace("～", "~").replace("：", ":")
    rules = []
    for days, rest in re.findall(r"\(([一二三四五六日~、,]+)\)\s*([^()]+)", t):
        ds = ",".join("-".join(DAY[x] for x in part.split("~")) for part in re.split(r"[、,]", days))
        rest = rest.strip()
        if re.search(r"不營業|休館|公休|休息", rest):
            rules.append(f"{ds} off"); continue
        spans = [f"{a.zfill(5)}-{b.zfill(5)}" for a, b in re.findall(r"(\d{1,2}:\d{2})\s*[~\-]\s*(\d{1,2}:\d{2})", rest)]
        if not spans: return ""
        rules.append(f"{ds} {','.join(spans)}")
    return "; ".join(rules)

# 其他連鎖：「平日：09:00-22:00 假日：10:00-22:00」「週一~週五 7:30~18:00 例假日 9:00~18:00」「09:00-22:00」
LABEL = [("週日/國定假日", "Su"), ("週一~週五", "Mo-Fr"), ("週一～週五", "Mo-Fr"), ("週六~週日", "Sa-Su"), ("週六～週日", "Sa-Su"),
         ("例假日", "Sa-Su"), ("平日", "Mo-Fr"), ("假日", "Sa-Su"), ("星期六", "Sa"), ("週六", "Sa"), ("星期日", "Su"), ("週日", "Su")]
TR = r"(\d{1,2}[:：]\d{2})\s*[-~～–]\s*(\d{1,2}[:：]\d{2})"
def gen_oh(t):
    t = t.replace("：", ":")
    lab = "|".join(re.escape(l) for l, _ in LABEL)
    parts = re.findall(rf"({lab})\s*[:：]?\s*(?:{TR}|(公休|店休))", t)
    if not parts:
        m = re.search(TR, t)
        return f"Mo-Su {m.group(1).zfill(5)}-{m.group(2).zfill(5)}" if m else ""
    seen, rules = set(), []
    for l, a, b, closed in parts:
        d = dict(LABEL)[l]
        if d in seen: continue
        seen.add(d)
        rules.append(f"{d} off" if closed else f"{d} {a.replace('：', ':').zfill(5)}-{b.replace('：', ':').zfill(5)}")
    return "; ".join(rules)

def akey(a):  # 地址比對鍵：路名＋巷弄＋門牌，去掉縣市、區、里、樓層
    a = (a or "").translate({0xFF10 + i: 0x30 + i for i in range(10)}).replace(" ", "").replace("－", "-").replace("臺", "台")
    a = re.sub(r"^\d{3,6}", "", a).replace("高雄市", "")
    a = re.sub(r"^.{1,3}區", "", a); a = re.sub(r"^.{1,3}里(\d+鄰)?", "", a)
    m = re.search(r"([^\d區里鄰]+?(?:路|街|大道)(?:[一二三四五六七八九十]+段)?(?:\d+巷)?(?:\d+弄)?\d+(?:[-之]\d+)?號)", a)
    return m.group(1).replace("-", "之") if m else ""

chains = []
for line in (l for cp in chain_paths for l in open(cp, encoding="utf-8")):
    parts = line.rstrip("\n").split("|")
    if len(parts) != 6: continue   # 格式不對的行直接略過
    tag, name, lat, lon, hrs, addr = parts
    if not lat:   # 沒座標：之後用地址對到登記店家
        oh = gen_oh(hrs)
        if oh: chains.append(dict(k="f" if tag == "CA" else "t", name=name, p=None, oh=oh, akey=akey(addr), addr=addr))
        continue
    oh = sb_oh(hrs)
    a = re.sub(r"^(.{2,3}區)\1", r"\1", addr.replace("高雄市", ""))
    chains.append(dict(k="f", name=name, p=(float(lat), float(lon)), oh=oh, addr=a))
print("chain stores with parsed hours:", sum(1 for c in chains if c["oh"]), "/", len(chains), " (no coords:", sum(1 for c in chains if not c["p"]), ")")

# ---- convenience: 萊爾富 (official coords) and 全家 non-24
conv_osm = [o for o in osm if o["k"] == "c"]
def conv_match(p, word, r=60):
    best = None
    for o in conv_osm:
        if word not in (o["name"] + o["brand"]): continue
        d = dist(p, o["p"])
        if d <= r and (best is None or d < best[0]): best = (d, o)
    return best[1]["oh"] if best else ""

hl_oh = 0
for row in S["hl"]:
    base = row[:6] + [None] * (6 - len(row[:6]))
    oh = conv_match(ll(base[4], base[5]), "萊爾富") if base[4] is not None else ""
    if oh: hl_oh += 1
    row[:] = base + [oh]
fam_oh = 0
for row in S["fam"]:
    row[:] = row[:5]
    oh = conv_match(ll(row[1], row[2]), "全家") if row[4] else ""
    if oh: fam_oh += 1
    row.append(oh)
print("萊爾富 hours:", hl_oh, "/", len(S["hl"]), " 全家 non-24 hours:", fam_oh, "/", sum(1 for r in S["fam"] if r[4]))

# ---- tea / cafe registry shops
shops = [r[:5] for r in S["shop"]]
pts = [ll(r[3], r[4]) for r in shops]
G = Grid(pts)
oh_of, disp_of, src_of, used = {}, {}, {}, set()
by_addr = {}
for k, r in enumerate(shops):
    key = akey(r[1])
    if key: by_addr.setdefault(key, []).append(k)
amatch = 0
for c in [c for c in chains if not c["p"]]:
    ks = [k for k in by_addr.get(c["akey"], []) if k not in used]
    if not ks: continue
    k = ks[0]; used.add(k); oh_of[k] = c["oh"]; disp_of[k] = c["name"]; src_of[k] = "c"; amatch += 1
print("chain stores matched by address:", amatch, "/", sum(1 for c in chains if not c["p"]))
src = [dict(o, src="osm") for o in osm if o["k"] in "tf" and o["oh"]] + [dict(c, src="sb") for c in chains if c["oh"] and c["p"]]
added = []
for o in src:
    want_cafe = o["k"] == "f"
    name = o["name"] or o.get("brand") or ""
    if o["src"] == "osm" and o.get("branch") and o["branch"] not in name: name = f"{name} {o['branch']}"
    GENERIC = set("咖啡茶飲料店坊館屋冷紅綠奶鮮手搖工作室企業社商行小吃部高雄門市分")
    words = set(re.findall(r"[\u4e00-\u9fff]", name + (o.get("brand") or ""))) - GENERIC
    def ok(d, k):
        reg = shops[k][0]
        if len(words & set(reg)) >= 2: return d <= 40          # 名字對得上
        if re.search(r"公司|股份", reg): return d <= 30          # 登記的是公司名，看不出店名
        return d <= 6                                            # 名字對不上，只接受幾乎同一點
    cands = [(d, k) for d, k in G.near(o["p"], 40) if k not in used and ok(d, k)]
    same = [(d, k) for d, k in cands if (shops[k][2] == 1) == want_cafe]
    pick = (same or cands or [None])[0]
    if not pick and G.near(o["p"], 8): continue   # 旁邊已有別間店、又對不上，寧可不加以免重複
    if pick:
        k = pick[1]; used.add(k); oh_of[k] = o["oh"]; src_of[k] = "s" if o["src"] == "sb" else "o"
        if name: disp_of[k] = name
    else:
        a, b = off(*o["p"])
        added.append([name or ("咖啡廳" if want_cafe else "手搖飲"), o.get("addr", ""), 1 if want_cafe else 0, a, b, o["oh"], "", "S" if o["src"] == "sb" else "O"])
for k, r in enumerate(shops):
    r += [oh_of.get(k, ""), disp_of.get(k, "") if disp_of.get(k, "") != r[0] else "", src_of.get(k, "")]
S["shop"] = shops + added
print("registry shops given hours:", len(oh_of), " new shops added:", len(added),
      " total shops with hours:", sum(1 for r in S["shop"] if r[5]), "/", len(S["shop"]))
S["src"]["hours"] = "營業時間：OpenStreetMap、星巴克官網（2026-11-15）"
json.dump(S, open(stores_path, "w"), ensure_ascii=False, separators=(",", ":"))
