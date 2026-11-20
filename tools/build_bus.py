# 把 TDX 高雄市公車資料轉成 App 用的小檔
#   bus.json       路線方向、實體站位（真實位置）、站牌群組（同名且 250 公尺內的站位）
#   bus_shape.json 每個路線方向的線型（Google encoded polyline，App 點路線時才載入）
# 用法：python tools/build_bus.py <StopOfRoute.json> <Route.json> <Shape.json>
import json, sys, math, collections, datetime
sor, routes, shapes = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4])
dist = lambda a, b: math.hypot((a[0] - b[0]) * 110540, (a[1] - b[1]) * 101750)

# 路線方向：[子路線名, 方向, 終點站名, 子路線ID(去掉 KHH)]
lines, lkey = [], {}
for e in sorted(sor, key=lambda e: (e["SubRouteName"]["Zh_tw"], e["Direction"])):
    k = (e["SubRouteUID"], e["Direction"])
    if k in lkey or not e["Stops"]: continue
    lkey[k] = len(lines)
    lines.append([e["SubRouteName"]["Zh_tw"], e["Direction"], e["Stops"][-1]["StopName"]["Zh_tw"], e["SubRouteUID"].replace("KHH", "", 1)])

# 實體站位（StationID）→ 經過的 [路線方向, 站序, StopID]
st = {}
for e in sor:
    li = lkey.get((e["SubRouteUID"], e["Direction"]))
    if li is None: continue
    for s in e["Stops"]:
        p = (s["StopPosition"]["PositionLat"], s["StopPosition"]["PositionLon"])
        x = st.setdefault(s["StationID"], {"n": s["StopName"]["Zh_tw"], "p": p, "e": []})
        x["e"].append([li, s["StopSequence"], s["StopID"]])

# 同名、250 公尺內的站位併成一個站（地圖縮小時顯示一個點），但每個實體站位（馬路兩側、各月台）都保留真實位置
by_name = collections.defaultdict(list)
for sid, x in st.items(): by_name[x["n"]].append(x)
stations, groups = [], []
for n, xs in by_name.items():
    left = xs[:]
    while left:
        g = [left.pop()]
        changed = True
        while changed:
            changed = False
            for x in left[:]:
                if any(dist(x["p"], y["p"]) < 250 for y in g): g.append(x); left.remove(x); changed = True
        g.sort(key=lambda x: -len(x["e"]))           # 路線最多的站位排第一，地圖縮小時點就放在它的位置
        idx = []
        for x in g:
            ent = sorted({tuple(e) for e in x["e"]})
            idx.append(len(stations))
            stations.append([round(x["p"][0] * 1e5), round(x["p"][1] * 1e5), [v for e in ent for v in (e[0], e[1], int(e[2]))]])
        groups.append([n, idx])
groups.sort(key=lambda g: (stations[g[1][0]][0], stations[g[1][0]][1]))

shape = {}
for s in shapes:
    li = lkey.get((s.get("SubRouteUID") or s["RouteUID"], s.get("Direction", 0)))
    if li is not None and s.get("EncodedPolyline"): shape[li] = s["EncodedPolyline"]
v = max(e.get("UpdateTime", "") for e in sor)[:10]
json.dump({"v": v, "lines": lines, "stations": stations, "groups": groups}, open("bus.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump({"v": v, "shape": {str(k): s for k, s in shape.items()}}, open("bus_shape.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("lines", len(lines), "stations", len(stations), "groups", len(groups), "shapes", len(shape), "version", v)
