# 從財政部「全國營業(稅籍)登記資料集」挑出高雄市營業中的手搖飲店、咖啡館、茶館，
# 加上萊爾富門市清單，輸出待比對地址檔 data/need.json（下一步用高雄市門牌坐標比對位置）
import csv, io, json, re, urllib.request, zipfile, datetime, collections
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url, t=300):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r: return r.read()
z = zipfile.ZipFile(io.BytesIO(get("https://eip.fia.gov.tw/data/BGMOPEN1.zip")))
raw = z.open(z.namelist()[0]).read()
try: text = raw.decode("utf-8-sig")
except UnicodeDecodeError: text = raw.decode("cp950", "replace")
rows = csv.reader(io.StringIO(text))
header = next(rows); date_row = next(rows)
CODES = {"563112": "cafe", "563113": "tea", "563115": "tea", "563199": "other"}
DRINK = re.compile(r"茶|飲|奶|果汁|冰|咖啡|coffee|cafe|café|珍珠|豆花|紅茶|綠茶", re.I)
COFFEE = re.compile(r"咖啡|coffee|cafe|café|珈琲|咖啡館|星巴克|路易莎|cama", re.I)
shops, stat = [], collections.Counter()
for r in rows:
    if len(r) < 16 or not r[0].startswith("高雄市"): continue
    codes = [r[8], r[10], r[12], r[14]]
    hit = [CODES[c] for c in codes if c in CODES]
    if not hit: continue
    name = r[3].strip()
    if hit[0] == "other" and not DRINK.search(name): continue
    if "cafe" in hit or (COFFEE.search(name) and "tea" not in hit[:1]): cat = "cafe"
    else: cat = "tea"
    stat[cat] += 1
    shops.append([r[1], name, r[0].strip(), cat])
hl = [l.split(" ") for l in open("tools/hilife.txt", encoding="utf-8").read().strip().split("\n")]
hl = [[p[1], " ".join(p[2:-1]), int(p[-1])] for p in hl]
out = {"v": date_row[0], "built": datetime.date.today().isoformat(), "shops": shops, "hl": hl}
import os; os.makedirs("data", exist_ok=True)
json.dump(out, open("data/need.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("tax data date", date_row[0], "shops", len(shops), dict(stat), "hilife", len(hl))
