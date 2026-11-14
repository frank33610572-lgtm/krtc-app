import urllib.request, urllib.parse, time
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(url, t=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r: return r.status, r.read()
for a in ["高雄市三民區建工路304號", "高雄市前金區新田路323號", "高雄市三民區中庸街1號"]:
    for base in ["https://api.nlsc.gov.tw/idc/TextQueryMap/", "https://api.nlsc.gov.tw/other/TextQueryMap/"]:
        try:
            s, b = get(base + urllib.parse.quote(a))
            print("NLSC", base.split("/")[-3], a, s, b[:400].decode("utf-8", "replace").replace("\n", " "))
        except Exception as e:
            print("NLSC", base.split("/")[-3], a, "ERR", e)
        time.sleep(0.5)
for u in ["https://data.kcg.gov.tw/", "https://openapi.kcg.gov.tw/", "https://scidm.nchc.org.tw/dataset?q=%E9%AB%98%E9%9B%84%E5%B8%82%E9%96%80%E7%89%8C%E5%9D%90%E6%A8%99"]:
    try: s, b = get(u, 20); print("REACH", u, s, len(b))
    except Exception as e: print("REACH", u, "ERR", e)
