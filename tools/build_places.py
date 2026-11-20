"""Merge geocoded coordinates (from the browser) into krtc-app/stores.json.

geo string: 9 chars per entry, first len(need.shops) entries for shops, then need.hl.
lat = (int(s[0:4],36)+2245000)/1e5, lon = (int(s[4:8],36)+12015000)/1e5, q = s[8]
'~~~~~~~~~' = no match.
"""
import json, sys

geo_path, need_path, stores_path = sys.argv[1:4]
geo = open(geo_path).read().replace("\n", "").strip()
need = json.load(open(need_path))
stores = json.load(open(stores_path))
n_shop, n_hl = len(need["shops"]), len(need["hl"])
assert len(geo) == 9 * (n_shop + n_hl), (len(geo), 9 * (n_shop + n_hl))

def dec(s):
    if s.startswith("~"):
        return None
    lat = (int(s[0:4], 36) + 2245000) / 1e5
    lon = (int(s[4:8], 36) + 12015000) / 1e5
    assert 22.4 < lat < 23.5 and 120.1 < lon < 121.1, (s, lat, lon)
    return lat, lon, s[8]

ents = [dec(geo[i:i + 9]) for i in range(0, len(geo), 9)]
off = lambda lat, lon: [round(lat * 1e5) - 2200000, round(lon * 1e5) - 12000000]

# 類別：0 手搖飲、1 咖啡廳、2 酒吧、3 餐廳
CAT = {"tea": 0, "cafe": 1, "bar": 2, "food": 3}
# 「飲酒店」登記裡有不少是視聽歌唱、會館、茶室類，不是一般人要找的酒吧
NOT_BAR = __import__("re").compile(r"會館|視聽|小吃部|小吃店|卡拉|KTV|好樂迪|錢櫃|娛樂|茶室|冷飲|飲料|美食|俱樂部|聯誼|食品", __import__("re").I)
shops, miss, dropped = [], 0, 0
SUB = {"561111": 4, "561112": 5, "561113": 6, "561114": 7, "561200": 8}   # 餐廳細類（其餘餐廳是 3）
for (uid, name, addr, cat, *code), e in zip(need["shops"], ents[:n_shop]):
    if not e:
        miss += 1
        continue
    if cat == "bar" and NOT_BAR.search(name):
        dropped += 1
        continue
    a, o = off(e[0], e[1])
    addr = addr.translate({0xFF10 + i: 0x30 + i for i in range(10)}).replace("－", "-").replace("高雄市", "", 1)
    shops.append([name, addr, SUB.get(code[0] if code else "", CAT[cat]) if cat == "food" else CAT[cat], a, o])

hl = []
for row, e in zip(stores["hl"], ents[n_shop:]):
    row = row[:4]
    hl.append(row + (off(e[0], e[1]) if e else []))

stores["hl"] = hl
stores["shop"] = shops
stores["src"]["shop"] = "財政部營業稅籍登記（" + need["v"] + "）＋高雄市門牌座標"
json.dump(stores, open(stores_path, "w"), ensure_ascii=False, separators=(",", ":"))
print("shops", len(shops), "miss", miss, "bar dropped", dropped, "by cat", __import__("collections").Counter(r[2] for r in shops), "hl with coords", sum(len(r) > 4 for r in hl), "/", len(hl))
