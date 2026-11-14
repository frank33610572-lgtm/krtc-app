# 探查政府開放資料的下載網址與格式
import json, urllib.request, io, zipfile, csv, sys
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url, n=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(n) if n else r.read()
for ds in ["167131", "32685", "28483"]:
    try:
        j = json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}"))
        r = j.get("result", j)
        print("==", ds, r.get("title"))
        for d in r.get("distribution", []):
            print("   ", d.get("resourceFormat"), d.get("resourceDownloadUrl"), d.get("resourceDescription"))
    except Exception as e:
        print("ERR", ds, e)
for url in ["https://eip.fia.gov.tw/data/BGMOPEN1.zip", "https://eip.fia.gov.tw/data/BGMOPEN1.csv"]:
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            print("HEAD", url, r.status, r.headers.get("Content-Length"), r.headers.get("Content-Type"))
    except Exception as e:
        print("HEAD ERR", url, e)
