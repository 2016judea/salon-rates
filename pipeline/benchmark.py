"""Shop-level base prices -> benchmark cells -> the JSON slices the site reads.

One number per shop per (service, size, tier): the shop's BASE price - the
cheapest listing that is a stand-alone base service at the shortest length the
menu offers (no length mod > short > medium; long/xl are surcharges, never base).
"From $X" contributes X and stays flagged as a floor; "$X-$Y" contributes X and
keeps Y. Prices are compared like with like: a posted price only against other
posted prices, a starting price ("from" or a range) only against other starting
prices, so a cell's key carries the kind. Tiers are never blended: the tier is
part of every key. Cells with fewer than MIN_SHOPS distinct shops are not
published. A shop whose own menu says its prices include the tip is flagged.
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
PRIV = HERE.parent / "private"  # every shop's prices: never served statically (scripts/build_public.py)
MIN_SHOPS = 5
LEN_PREF = {None: 0, "short": 1, "medium": 2}
# A menu line that says the price already includes the tip ("These prices reflect
# that this establishment no longer accepts tipping"). Narrow on purpose: "Tips
# included on how to keep that beard fresh" and "Gratuity NOT included" must not match.
NO_TIP = re.compile(r"no longer accept\w* tip|no[- ]tipping|tip[- ]free|tipless|"
                    r"(?:do not|don't|does not|doesn't|not) accept(?:ing)? tips|"
                    r"gratuity (?:is )?included|tips? (?:is |are )?included in (?:the |all |our )?pric", re.I)

DDL = """
DROP TABLE IF EXISTS shop_price;
CREATE TABLE shop_price (venue_id TEXT, code TEXT, size_mod TEXT, tier TEXT,
  price REAL, price_type TEXT, duration_min INTEGER, listing_id TEXT, price_max REAL,
  PRIMARY KEY (venue_id, code, size_mod, tier));
DROP TABLE IF EXISTS benchmark;
CREATE TABLE benchmark (code TEXT, size_mod TEXT, geo_type TEXT, geo_key TEXT, tier TEXT,
  business_type TEXT, kind TEXT, n_shops INTEGER, n_from INTEGER, p25 REAL, median REAL, p75 REAL,
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
    return dict(n_shops=len(vals), n_from=sum(v["ptype"] != "fixed" for v in vals),
                p25=round(quant(prices, .25), 2), median=round(statistics.median(prices), 2),
                p75=round(quant(prices, .75), 2), min=min(prices), max=max(prices),
                per_min_median=round(statistics.median(per_min), 3) if len(per_min) >= MIN_SHOPS else None)


def main():
    db = sqlite3.connect(DB)
    db.executescript(DDL)
    rows = db.execute("""
      SELECT b.venue_id, m.code, COALESCE(m.size_mod,''), m.tier, m.length_mod, l.price_min, l.price_type,
             l.duration_min, l.listing_id, l.price_max
      FROM service_listing l JOIN listing_map m USING(listing_id) JOIN business b USING(business_id)
      WHERE m.code IS NOT NULL AND m.is_base=1 AND l.price_type IN ('fixed','from','range')
        AND l.price_min >= 5  -- $0.01 / $1 are 'ask me' placeholders""").fetchall()
    best = {}
    for venue, code, size, tier, length, price, ptype, dur, lid, pmax in rows:
        key = (venue, code, size, tier)
        rank = (LEN_PREF.get(length, 3), price)
        if rank[0] > 2:
            continue
        if key not in best or rank < best[key][0]:
            best[key] = (rank, price, ptype, dur, lid, pmax if ptype == "range" and pmax and pmax > price else None)
    # A price 5x the metro median of its service (or a fifth of it) is a typo on the
    # menu ($2,000 box braids where the metro middle is $150), not a market price.
    by_key = collections.defaultdict(list)
    for (venue, code, size, tier), v in best.items():
        by_key[(code, size, tier)].append(v[1])
    mids = {k: statistics.median(v) for k, v in by_key.items()}
    dropped = [k for k, v in best.items() if not (mids[k[1:]] / 5 <= v[1] <= mids[k[1:]] * 5)]
    for k in dropped:
        del best[k]
    print(f"dropped {len(dropped)} menu typos (over 5x or under 1/5 of the metro median)")
    db.executemany("INSERT INTO shop_price VALUES (?,?,?,?,?,?,?,?,?)",
                   [(*k, v[1], v[2], v[3], v[4], v[5]) for k, v in best.items()])
    no_tip = {vid for vid, d in db.execute("""SELECT b.venue_id, l.description FROM service_listing l
        JOIN business b USING(business_id) WHERE l.description IS NOT NULL""") if NO_TIP.search(d)}
    print(f"shops whose own menu says the price includes the tip: {len(no_tip)}")

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
        kind = "fixed" if v[2] == "fixed" else "from"
        for btype in ("all", ven["type"]):
            groups[(code, size, "metro", "Twin Cities", tier, btype, kind)].append(rec)
            groups[(code, size, "city", ven["city"], tier, btype, kind)].append(rec)
    today = date.today().isoformat()
    bench = []
    for k, vals in groups.items():
        if len(vals) < MIN_SHOPS:
            continue
        c = cell(vals)
        db.execute("INSERT INTO benchmark VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (*k, c["n_shops"], c["n_from"], c["p25"], c["median"], c["p75"], c["min"], c["max"],
                    c["per_min_median"], today))
        bench.append(dict(code=k[0], size=k[1], geo=k[2], key=k[3], tier=k[4], type=k[5], kind=k[6], **c))
    db.commit()

    # slices
    OUT.mkdir(parents=True, exist_ok=True)
    priced = collections.defaultdict(list)
    for (vid, code, size, tier), v in best.items():
        # [code, size, tier, price, 0 posted | 1 starting, minutes, range top or null]
        priced[vid].append([code, size, tier, v[1], 0 if v[2] == "fixed" else 1, v[3], v[5]])
    shops = []
    for vid, ven in venues.items():
        if vid in priced:
            s = dict(ven)
            s["p"] = sorted(priced[vid], key=lambda p: p[:4])
            if vid in no_tip:
                s["nt"] = 1
            shops.append(s)
    shops.sort(key=lambda s: s["name"].lower())
    from taxonomy import CODES
    used = {b["code"] for b in bench if b["geo"] == "metro"}
    services = [dict(code=c, family=f, label=l) for c, f, l in CODES if c in used]
    # "built" is the day the menus were read, not the day this script ran: the page says
    # "read <built>", and a rebuild from the cache must not make old prices look new.
    read_on = db.execute("SELECT MAX(snapshot_date) FROM service_listing").fetchone()[0]
    meta = dict(built=read_on, shops=len(shops), min_shops=MIN_SHOPS, no_tip=sum(s.get("nt", 0) for s in shops),
                sources=sorted({v["source"] for v in venues.values()}))
    PRIV.mkdir(parents=True, exist_ok=True)
    (PRIV / "shops.json").write_text(json.dumps(shops, separators=(",", ":")))
    (PRIV / "benchmarks.json").write_text(json.dumps(bench, separators=(",", ":")))
    (OUT / "services.json").write_text(json.dumps(dict(meta=meta, services=services), separators=(",", ":")))
    print(f"shops with a price {len(shops)}; shop-prices {len(best)}; published cells {len(bench)}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    main()
