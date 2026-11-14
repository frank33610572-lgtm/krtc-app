import urllib.request, urllib.parse, json, re
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url, t=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r: return r.read()
q = urllib.parse.quote("高雄市 門牌坐標")
for api in [f"https://scidm.nchc.org.tw/api/3/action/package_search?q={q}&rows=10", f"https://ark.nchc.org.tw/api/3/action/package_search?q={q}&rows=10"]:
    try:
        j = json.loads(get(api))
        for p in j["result"]["results"]:
            print("PKG", p.get("title"), p.get("name"))
            for r in p.get("resources", [])[:4]:
                print("   RES", r.get("format"), r.get("url"), r.get("name"))
    except Exception as e:
        print("ERR", api[:40], e)
