# 抓高雄市公車資料（TDX 運輸資料流通服務平臺，免登入額度）存到 bus/
#   路線 Route、路線站序 StopOfRoute、線型 Shape、班表 Schedule、車輛 Vehicle、業者 Operator
#   另外各抓一次即時資料當樣本：定時定位 A1（含車牌）、預估到站 N1
import json, os, time, urllib.request, urllib.error, gzip
BASE = "https://tdx.transportdata.tw/api/basic/v2/Bus"
EPS = {"route": "Route/City/Kaohsiung", "stop_of_route": "StopOfRoute/City/Kaohsiung", "shape": "Shape/City/Kaohsiung",
       "schedule": "Schedule/City/Kaohsiung", "vehicle": "Vehicle/City/Kaohsiung", "operator": "Operator/City/Kaohsiung",
       "realtime_a1": "RealTimeByFrequency/City/Kaohsiung", "eta_n1": "EstimatedTimeOfArrival/City/Kaohsiung"}
os.makedirs("bus", exist_ok=True)
def get(path):
    for i in range(6):
        try:
            req = urllib.request.Request(f"{BASE}/{path}?$format=JSON", headers={"User-Agent": "krtc-app", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read(); return json.loads(gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b)
        except urllib.error.HTTPError as e:
            print(" ", path, "HTTP", e.code, e.read()[:200]); time.sleep(20 * (i + 1))
        except Exception as e:
            print(" ", path, "ERR", e); time.sleep(10)
    return None
for k, p in EPS.items():
    d = get(p)
    if d is None: print(k, "FAILED"); continue
    json.dump(d, open(f"bus/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(k, len(d), "records", os.path.getsize(f"bus/{k}.json") // 1024, "KB")
    time.sleep(3)
