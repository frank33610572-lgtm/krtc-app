# 餐廳再分細類：用稅籍登記的行業代號，把 data/stores_base.json 裡的餐廳（類別 3）改成 3–8
#   3 餐廳（561115 餐廳、561116 有娛樂節目餐廳、561117 吃到飽）
#   4 早餐（561111）  5 便當自助餐（561112）  6 麵店小吃（561113）  7 速食（561114）  8 小吃攤（561200）
# 用法：python tools/add_subtypes.py data/stores_base.json
import csv, io, sys, json, urllib.request, zipfile, collections
SUB = {"561111": 4, "561112": 5, "561113": 6, "561114": 7, "561200": 8, "561115": 3, "561116": 3, "561117": 3}
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request("https://eip.fia.gov.tw/data/BGMOPEN1.zip", headers=UA), timeout=300).read()))
raw = z.open(z.namelist()[0]).read()
try: text = raw.decode("utf-8-sig")
except UnicodeDecodeError: text = raw.decode("cp950", "replace")
norm = lambda a: a.strip().translate({0xFF10 + i: 0x30 + i for i in range(10)}).replace("－", "-").replace("高雄市", "", 1)
code_of, by_name = {}, collections.defaultdict(set)
rows = csv.reader(io.StringIO(text)); next(rows); next(rows)
for r in rows:
    if len(r) < 16 or not r[0].startswith("高雄市"): continue
    c = next((c for c in (r[8], r[10], r[12], r[14]) if c in SUB), None)
    if not c: continue
    code_of[(r[3].strip(), norm(r[0]))] = SUB[c]
    by_name[r[3].strip()].add(SUB[c])
p = sys.argv[1]; S = json.load(open(p, encoding="utf-8"))
stat = collections.Counter()
for row in S["shop"]:
    if row[2] < 3: continue
    sub = code_of.get((row[0], row[1]))
    if sub is None and len(by_name.get(row[0], ())) == 1: sub = next(iter(by_name[row[0]]))   # 地址寫法不同但店名唯一
    if sub is None: stat["miss"] += 1; continue
    row[2] = sub; stat[sub] += 1
json.dump(S, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("subtypes", dict(stat))
