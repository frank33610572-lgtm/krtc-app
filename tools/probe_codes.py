# 一次性：列出高雄市稅籍登記中 56 開頭（餐飲業）行業代號的家數與範例店名
import csv, io, urllib.request, zipfile, collections, random
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
raw = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request("https://eip.fia.gov.tw/data/BGMOPEN1.zip", headers=UA), timeout=300).read()))
f = raw.open(raw.namelist()[0]).read()
try: text = f.decode("utf-8-sig")
except UnicodeDecodeError: text = f.decode("cp950", "replace")
rows = csv.reader(io.StringIO(text)); header = next(rows); print(header); print(next(rows))
cnt, names, ex = collections.Counter(), {}, collections.defaultdict(list)
for r in rows:
    if len(r) < 16 or not r[0].startswith("高雄市"): continue
    c = r[8]
    if not c.startswith("56"): continue
    cnt[c] += 1; names[c] = r[9]
    if len(ex[c]) < 400: ex[c].append(r[3])
random.seed(1)
for c, n in sorted(cnt.items()):
    print(c, names[c], n, "|", "、".join(random.sample(ex[c], min(25, len(ex[c])))))
