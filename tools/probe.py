import json, urllib.request, io, zipfile, csv, sys, collections, socket
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url, t=60, n=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r: return r.read(n) if n else r.read()
def dec(b):
    for enc in ("utf-8-sig", "big5", "cp950"):
        try: return b.decode(enc)
        except: pass
    return b.decode("utf-8", "replace")
def tryit(name, fn):
    try: fn()
    except Exception as e: print(name, "ERR", type(e).__name__, e)
tryit("KCG-openapi", lambda: print("KCG-openapi", dec(get("https://openapi.kcg.gov.tw/Api/Service/Get/eb12ff9e-3792-494e-99bf-71d9f08eaaa4", 40, 1500))[:600]))
tryit("KCG-file", lambda: print("KCG-file", len(get("https://data.kcg.gov.tw/File/DirectDownload/eb12ff9e-3792-494e-99bf-71d9f08eaaa4", 40, 2000))))
def biz():
    t = dec(get("https://data.gcis.nat.gov.tw/od/file?oid=6EFF6E6F-832B-4FF2-972E-EBB102732969", 120))
    L = t.splitlines(); k = [l for l in L if "高雄市" in l]
    print("BIZ lines", len(L), "khh", len(k)); print("BIZ head", L[:2]); print("BIZ sample", k[:4])
tryit("BIZ", biz)
def tax():
    z = zipfile.ZipFile(io.BytesIO(get("https://eip.fia.gov.tw/data/BGMOPEN1.zip", 300)))
    print("ZIP", z.namelist())
    with z.open(z.namelist()[0]) as f:
        raw = f.read()
    t = dec(raw); L = t.splitlines()
    print("TAX lines", len(L)); print("TAX head", L[:3])
    hdr = next(csv.reader([L[1] if "統一" in L[1] else L[0]]))
    print("TAX hdr", hdr)
    cnt = collections.Counter(); sample = collections.defaultdict(list)
    for l in L:
        if "高雄市" not in l: continue
        for code in ("563112", "563113", "563115", "563199", "5631-12", "5631-15"):
            if code in l:
                cnt[code] += 1
                if len(sample[code]) < 3: sample[code].append(l[:220])
    print("TAX khh counts", dict(cnt))
    for c, s in sample.items(): print("TAX sample", c, s)
tryit("TAX", tax)
