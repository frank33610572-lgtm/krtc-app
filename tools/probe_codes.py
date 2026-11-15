# 一次性：測試能否從 GitHub Actions 取得高雄市門牌坐標資料
import urllib.request, re, time, json
UA = {"User-Agent": "Mozilla/5.0 krtc-app data builder"}
def get(u, t=60):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r: return r.read()
for page in ["https://data.kcg.gov.tw/DataSet/Detail/b9579154-2b39-40f3-aacd-4d160029fbb9", "https://data.kcg.gov.tw/dataset?q=%E9%96%80%E7%89%8C%E5%9D%90%E6%A8%99"]:
    try:
        h = get(page).decode("utf-8", "replace")
        print("OK", page, len(h))
        print(sorted(set(re.findall(r"https?://api\.kcg\.gov\.tw[^\"'<> ]+", h)))[:20])
        print(sorted(set(re.findall(r"/[Dd]ata[Ss]et/[Dd]etail/[0-9a-f-]{36}", h)))[:40])
        for m in re.finditer(r"門牌坐標[^<]{0,40}", h): print(" ", m.group(0))
    except Exception as e: print("ERR", page, e)
