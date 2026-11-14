import json, urllib.request, io, zipfile, csv, sys, collections
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r: return r.read()
def dec(b):
    for enc in ("utf-8-sig", "big5", "cp950"):
        try: return b.decode(enc)
        except: pass
    return b.decode("utf-8", "replace")
# 1 行業代號
t = dec(get("https://service.mof.gov.tw/public/Data/statistic/class/tsic.csv"))
rows = list(csv.reader(io.StringIO(t)))
print("TSIC header", rows[0])
for r in rows:
    if any(k in "".join(r) for k in ("飲料店", "咖啡", "茶", "冰果")) and r and r[0] in ("9", "9.0", "第9次", rows[-1][0]):
        print("TSIC", r[:4])
print("TSIC versions", collections.Counter(r[0] for r in rows[1:]).most_common(5))
# 2 門牌
b = get("https://data.kcg.gov.tw/File/DirectDownload/eb12ff9e-3792-494e-99bf-71d9f08eaaa4")
t = dec(b); L = t.splitlines()
print("ADDR bytes", len(b), "lines", len(L)); print("ADDR head", L[:4])
# 3 商業登記 飲料店
t = dec(get("https://data.gcis.nat.gov.tw/od/file?oid=6EFF6E6F-832B-4FF2-972E-EBB102732969"))
L = t.splitlines(); k = [l for l in L if "高雄市" in l]
print("BIZ lines", len(L), "khh", len(k)); print("BIZ head", L[:2]); print("BIZ khh sample", k[:5])
print("BIZ status", collections.Counter(l.split(",")[-2] if l.count(",")>=3 else "?" for l in k).most_common(6))
# 4 稅籍
z = zipfile.ZipFile(io.BytesIO(get("https://eip.fia.gov.tw/data/BGMOPEN1.zip")))
print("ZIP names", z.namelist())
with z.open(z.namelist()[0]) as f:
    head = f.read(3000)
print("TAX head", dec(head).splitlines()[:4])
