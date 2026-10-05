"""Shop-level base prices -> benchmark cells -> the JSON slices the site reads.

One number per shop per (service, size, tier): the shop's BASE price - the
cheapest listing that is a stand-alone base service at the shortest length the
menu offers (no length mod > short > medium; long/xl are surcharges, never base).
"From $X" contributes X and stays flagged as a floor. Tiers are never blended:
the tier is part of every key. Cells with fewer than MIN_SHOPS distinct shops
are not published.
"""
import collections
import json
import re
import sqlite3
import statistics
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "salon.db"
OUT = HERE.parent / "site" / "data"
MIN_SHOPS = 5
LEN_PREF = {None: 0, "short": 1, "medium": 2}

DDL = """
DROP TABLE IF EXISTS shop_price;
CREATE TABLE shop_price (venue_id TEXT, code TEXT, size_mod TEXT, tier TEXT,
  price REAL, price_type TEXT, duration_min INTEGER, listing_id TEXT,
  PRIMARY KEY (venue_id, code, size_mod, tier));
DROP TABLE IF EXISTS benchmark;
CREATE TABLE benchmark (code TEXT, size_mod TEXT, geo_type TEXT, geo_key TEXT, tier TEXT,
  business_type TEXT, n_shops INTEGER, n_from INTEGER, p25 REAL, median REAL, p75 REAL,
  min REAL, max REAL, per_min_median REAL, computed_at TEXT);
"""

CITY_FIX = {"st paul": "Saint Paul", "st. paul": "Saint Paul", "saint paul": "Saint Paul",
            "st louis park": "St. Louis Park", "st. louis park": "St. Louis Park",
            "saint louis park": "St. Louis Park", "mpls": "Minneapolis",
            "west st paul": "West St. Paul", "west saint paul": "West St. Paul",
            "west st. paul": "West St. Paul", "south st paul": "South St. Paul",
            "north st paul": "North St. Paul", "saint anthony": "St. Anthony"}


def city_name(c):
    c = (c or "").strip()
    k = re.sub(r"\s+", " ", c.lower())
    return CITY_FIX.get(k, c.title() if c.islower() or c.isupper() else c)


def quant(xs, q):
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def cell(vals):
    prices = [v["price"] for v in vals]
    per_min = [v["price"] / v["dur"] for v in vals if v["dur"]]
    return dict(n_shops=len(vals), n_from=sum(v["ptype"] == "from" for v in vals),
                p25=round(quant(prices, .25), 2), median=round(statistics.median(prices), 2),
                p75=round(quant(prices, .75), 2), min=min(prices), max=max(prices),
                per_min_median=round(statistics.median(per_min), 3) if len(per_min) >= MIN_SHOPS else None)


def main():
    db = sqlite3.connect(DB)
    db.executescript(DDL)
    rows = db.execute("""
      SELECT b.venue_id, m.code, COALESCE(m.size_mod,''), m.tier, m.length_mod, l.price_min, l.price_type,
             l.duration_min, l.listing_id
      FROM service_listing l JOIN listing_map m USING(listing_id) JOIN business b USING(business_id)
      WHERE m.code IS NOT NULL AND m.is_base=1 AND l.price_type IN ('fixed','from','range')
        AND l.price_min >= 5  -- $0.01 / $1 are 'ask me' placeholders""").fetchall()
    best = {}
    for venue, code, size, tier, length, price, ptype, dur, lid in rows:
        key = (venue, code, size, tier)
        rank = (LEN_PREF.get(length, 3), price)
        if rank[0] > 2:
            continue
        if key not in best or rank < best[key][0]:
            best[key] = (rank, price, "from" if ptype in ("from", "range") else "fixed", dur, lid)
    db.executemany("INSERT INTO shop_price VALUES (?,?,?,?,?,?,?,?)",
                   [(*k, v[1], v[2], v[3], v[4]) for k, v in best.items()])

    venues = {}
    for vid, name, city, lat, lng, btype, url, source, rating, reviews in db.execute("""
        SELECT venue_id, name, city, lat, lng, business_type, url, source, rating, review_count
        FROM business WHERE business_id = venue_id"""):
        venues[vid] = dict(id=vid, name=name, city=city_name(city), lat=round(lat, 5), lng=round(lng, 5),
                           type=btype, url=url, source=source)
    # every platform a venue appears on
    for vid, src, url in db.execute("SELECT venue_id, source, url FROM business WHERE business_id != venue_id"):
        venues[vid].setdefault("also", []).append({"source": src, "url": url})

    groups = collections.defaultdict(list)
    for (vid, code, size, tier), v in best.items():
        ven = venues[vid]
        rec = dict(price=v[1], ptype=v[2], dur=v[3])
        for btype in ("all", ven["type"]):
            groups[(code, size, "metro", "Twin Cities", tier, btype)].append(rec)
            groups[(code, size, "city", ven["city"], tier, btype)].append(rec)
    today = date.today().isoformat()
    bench = []
    for k, vals in groups.items():
        if len(vals) < MIN_SHOPS:
            continue
        c = cell(vals)
        db.execute("INSERT INTO benchmark VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (*k, c["n_shops"], c["n_from"], c["p25"], c["median"], c["p75"], c["min"], c["max"],
                    c["per_min_median"], today))
        bench.append(dict(code=k[0], size=k[1], geo=k[2], key=k[3], tier=k[4], type=k[5], **c))
    db.commit()

    # slices
    OUT.mkdir(parents=True, exist_ok=True)
    priced = collections.defaultdict(list)
    for (vid, code, size, tier), v in best.items():
        priced[vid].append([code, size, tier, v[1], 1 if v[2] == "from" else 0, v[3]])
    shops = []
    for vid, ven in venues.items():
        if vid in priced:
            s = dict(ven)
            s["p"] = sorted(priced[vid])
            shops.append(s)
    shops.sort(key=lambda s: s["name"].lower())
    from taxonomy import CODES
    used = {b["code"] for b in bench if b["geo"] == "metro"}
    services = [dict(code=c, family=f, label=l) for c, f, l in CODES if c in used]
    meta = dict(built=today, shops=len(shops), min_shops=MIN_SHOPS,
                sources=sorted({v["source"] for v in venues.values()}))
    (OUT / "shops.json").write_text(json.dumps(shops, separators=(",", ":")))
    (OUT / "benchmarks.json").write_text(json.dumps(bench, separators=(",", ":")))
    (OUT / "services.json").write_text(json.dumps(dict(meta=meta, services=services), separators=(",", ":")))
    print(f"shops with a price {len(shops)}; shop-prices {len(best)}; published cells {len(bench)}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    main()
