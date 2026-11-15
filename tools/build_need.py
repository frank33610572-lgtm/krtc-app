# 從財政部「全國營業(稅籍)登記資料集」挑出高雄市營業中的手搖飲店、咖啡館、酒吧、餐廳，
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
# 行業代號（財政部稅務行業標準分類）→ 好用地圖類別
#   手搖飲 tea：563115 手搖飲店、563200 調理飲料攤販、563199 其他飲料店（店名像飲料才算）
#   咖啡廳 cafe：563112 咖啡館
#   酒吧 bar：563114 飲酒店
#   餐廳 food：561111 早餐店、561112 便當自助餐、561113 麵店小吃店、561114 連鎖速食、561115 餐廳、
#             561116 有娛樂節目餐廳、561117 吃到飽、561200 餐食攤販
CODES = {"563115": "tea", "563200": "tea", "563199": "other", "563112": "cafe", "563114": "bar",
         "561111": "food", "561112": "food", "561113": "food", "561114": "food", "561115": "food",
         "561116": "food", "561117": "food", "561200": "food"}
DRINK = re.compile(r"茶|飲|奶|果汁|冰|咖啡|coffee|cafe|café|珍珠|豆花|紅茶|綠茶|豆漿|汁", re.I)
COFFEE = re.compile(r"咖啡|coffee|cafe|café|珈琲|咖啡館|星巴克|路易莎|cama", re.I)
BAR = re.compile(r"酒館|酒吧|酒場|酒肆|酒坊|居酒屋|小酒|餐酒|精釀|啤酒|調酒|威士忌|whisky|bar\b|pub\b|lounge|taproom", re.I)
shops, stat = [], collections.Counter()
for r in rows:
    if len(r) < 16 or not r[0].startswith("高雄市"): continue
    codes = [c for c in (r[8], r[10], r[12], r[14]) if c in CODES]
    if not codes: continue
    name = r[3].strip()
    first = CODES[codes[0]]                        # 以主要行業為準（第一個符合的代號）
    has = {CODES[c] for c in codes}
    if first == "other":
        if not DRINK.search(name): continue
        first = "tea"
    if first in ("tea", "food", "cafe") and BAR.search(name) and ("bar" in has or first == "food"): cat = "bar"
    elif first == "cafe" or (COFFEE.search(name) and (first == "tea" or "cafe" in has)): cat = "cafe"
    else: cat = first
    stat[cat] += 1
    shops.append([r[1], name, r[0].strip(), cat])
hl = [l.split(" ") for l in open("tools/hilife.txt", encoding="utf-8").read().strip().split("\n")]
hl = [[p[1], " ".join(p[2:-1]), int(p[-1])] for p in hl]
out = {"v": date_row[0], "built": datetime.date.today().isoformat(), "shops": shops, "hl": hl}
import os; os.makedirs("data", exist_ok=True)
json.dump(out, open("data/need.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("tax data date", date_row[0], "shops", len(shops), dict(stat), "hilife", len(hl))
import random; random.seed(7)
for c in ("tea", "cafe", "bar", "food"):
    print(c, "、".join(random.sample([s[1] for s in shops if s[3] == c], min(40, stat[c]))))
