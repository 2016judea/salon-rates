"""Parse every cached page into the raw tables of pipeline/salon.db (see SCHEMA.md).

Reads only the disk cache written by the crawlers, so it is free to re-run.
Raw rows are kept exactly as published: name, variant label, price as typed
(fixed / from / range / consult), duration. Mapping to canonical services is
map_services.py's job, not this file's."""
import gzip
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import path_for  # noqa: E402
from geo import in_metro, miles  # noqa: E402

HERE = Path(__file__).parent
CACHE = HERE / "cache"
DB = HERE / "salon.db"
SNAPSHOT = date.today().isoformat()

DDL = """
CREATE TABLE business (
  business_id TEXT PRIMARY KEY,      -- '<source>:<source id>'
  venue_id TEXT,                     -- same physical shop across platforms
  source TEXT, source_id TEXT, url TEXT,
  name TEXT, address TEXT, city TEXT, postal_code TEXT,
  lat REAL, lng REAL,
  category_raw TEXT,                 -- the platform's own category words
  business_type TEXT,                -- set by map_services.py
  is_suite INTEGER DEFAULT 0,        -- inside a salon-suite building (Sola, Phenix, ...)
  rating REAL, review_count INTEGER,
  captured_at TEXT
);
CREATE TABLE provider (
  provider_id TEXT PRIMARY KEY, business_id TEXT, name TEXT,
  tier_raw TEXT, tier TEXT
);
CREATE TABLE service_listing (
  listing_id TEXT,                   -- '<business_id>:<service id>:<variant id>'
  snapshot_date TEXT,
  business_id TEXT, provider_id TEXT,
  category_raw TEXT, name_raw TEXT, variant_raw TEXT,
  price_type TEXT,                   -- fixed | from | range | consult | free
  price_min REAL, price_max REAL,
  duration_min INTEGER, duration_max INTEGER,
  description TEXT, source TEXT,
  PRIMARY KEY (listing_id, snapshot_date)
);
"""

SUITE_RE = re.compile(r"\b(sola|phenix|salon lofts|my salon suite|salons by jc|suite studios|iconic salon suites|evolve salon suites|image studios)\b", re.I)


def gz(p):
    return gzip.decompress(p.read_bytes()).decode("utf-8", "replace")


def money(s):
    m = re.findall(r"\$?\s*([\d,]+(?:\.\d+)?)", s or "")
    return [float(x.replace(",", "")) for x in m]


# ---------------------------------------------------------------- Fresha
def fresha(db):
    slugs = (CACHE / "fresha_venues.txt").read_text().split()
    for slug in slugs:
        url = f"https://www.fresha.com/a/{slug}"
        p = path_for("fresha", url)
        if not p.exists():
            continue
        h = gz(p)
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', h, re.S)
        if not m:
            continue
        loc = json.loads(m.group(1))["props"]["pageProps"]["data"]["location"]
        a = loc["address"]
        bid = f"fresha:{loc['id']}"
        street = a.get("shortFormatted") or ""
        db.execute("INSERT OR REPLACE INTO business VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            bid, None, "fresha", str(loc["id"]), url, loc["name"], street, a.get("cityName"),
            a.get("postalCode"), a.get("latitude"), a.get("longitude"),
            (loc.get("primaryBusinessType") or {}).get("englishName"), None,
            int(bool(SUITE_RE.search(street + " " + loc["name"]))),
            loc.get("rating"), loc.get("reviewsCount"), SNAPSHOT))
        for cat in loc.get("services") or []:
            for it in cat.get("items") or []:
                if it.get("__typename") != "Service":
                    continue
                variants = it.get("variants") or [{"id": it["id"], "name": it["name"],
                                                   "formattedRetailPrice": it.get("formattedRetailPrice"),
                                                   "caption": it.get("caption")}]
                multi = len(variants) > 1
                for v in variants:
                    fp = v.get("formattedRetailPrice") or ""
                    nums = money(fp)
                    low = fp.lower()
                    if "free" in low:
                        ptype, lo, hi = "free", 0, 0
                    elif not nums:
                        ptype, lo, hi = "consult", None, None
                    elif "from" in low:
                        ptype, lo, hi = "from", nums[0], None
                    elif len(nums) > 1:
                        ptype, lo, hi = "range", nums[0], nums[-1]
                    else:
                        ptype, lo, hi = "fixed", nums[0], nums[0]
                    dur = parse_caption(v.get("caption"))
                    db.execute("INSERT OR REPLACE INTO service_listing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        f"{bid}:{it['serviceId']}:{v['id']}", SNAPSHOT, bid, None, cat.get("name"),
                        it["name"].strip(), (v.get("name") or "").strip() if multi else "",
                        ptype, lo, hi, dur, dur, it.get("description"), "fresha"))


def parse_caption(c):
    if not c:
        return None
    h = re.search(r"(\d+)\s*hr", c)
    m = re.search(r"(\d+)\s*min", c)
    t = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return t or None


# ---------------------------------------------------------------- Booksy
def nuxt_resolver(arr):
    wrappers = ("Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "Set", "Map")

    def res(i, depth=0):
        if not isinstance(i, int) or depth > 40:
            return i
        v = arr[i]
        if isinstance(v, dict):
            return {k: res(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in wrappers:
                return res(v[1], depth + 1) if len(v) > 1 else None
            return [res(x, depth + 1) for x in v]
        return v
    return res


def booksy_price(sp, typ, price):
    s = (sp or "").strip()
    nums = money(s)
    if typ == "F" or s.lower() == "free":
        return "free", 0, 0
    if not nums:
        return "consult", None, None
    if s.endswith("+"):
        return "from", nums[0], None
    if len(nums) > 1:
        return "range", nums[0], nums[-1]
    return "fixed", nums[0], nums[0]


def booksy(db):
    seen = set()
    for url in (CACHE / "booksy_candidates.txt").read_text().split():
        p = path_for("booksy", url)
        if not p.exists():
            continue
        h = gz(p)
        m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
        if not m:
            continue
        arr = json.loads(m.group(1))
        idx = next((i for i, v in enumerate(arr) if isinstance(v, dict) and "serviceCategories" in v
                    and "location" in v), None)
        if idx is None:
            continue
        b = nuxt_resolver(arr)(idx)
        loc = b.get("location") or {}
        co = loc.get("coordinate") or {}
        region = next((r["slug"] for r in b.get("regions") or [] if r.get("type") == "state"), None)
        if not in_metro(co.get("latitude"), co.get("longitude"), "MN" if region == "minnesota" else region):
            continue
        bid = f"booksy:{b['id']}"
        if bid in seen:
            continue
        seen.add(bid)
        cats = [c["name"] for c in b.get("businessCategories") or []]
        prim = next((c["name"] for c in b.get("businessCategories") or [] if c["id"] == b.get("primaryCategory")), None)
        addr = loc.get("address") or ""
        db.execute("INSERT OR REPLACE INTO business VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            bid, None, "booksy", str(b["id"]), url, b["name"], addr, loc.get("city"),
            (re.findall(r"\b(5\d{4})\b", addr) or [None])[-1], co.get("latitude"), co.get("longitude"),
            "|".join([prim or ""] + [c for c in cats if c != prim]), None,
            int(bool(SUITE_RE.search(addr + " " + b["name"] + " " + (b.get("umbrellaVenueName") or "")))),
            b.get("reviewsRank"), b.get("reviewsCount"), SNAPSHOT))
        staff = {s["id"]: s["name"] for s in b.get("staff") or []}
        for s in staff:
            db.execute("INSERT OR REPLACE INTO provider VALUES (?,?,?,?,?)",
                       (f"{bid}:{s}", bid, staff[s], None, None))
        for cat in b.get("serviceCategories") or []:
            for s in cat.get("services") or []:
                vs = s.get("variants") or []
                for v in vs:
                    ptype, lo, hi = booksy_price(v.get("servicePrice"), v.get("type"), v.get("price"))
                    sids = v.get("stafferId") or []
                    # A variant tied to exactly one staffer in a multi-staff shop is that
                    # person's own price; otherwise the price is the shop's.
                    prov = f"{bid}:{sids[0]}" if len(sids) == 1 and len(staff) > 1 else None
                    db.execute("INSERT OR REPLACE INTO service_listing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        f"{bid}:{s['id']}:{v['id']}", SNAPSHOT, bid, prov, cat.get("name"),
                        (s.get("name") or "").strip(), (v.get("label") or "").strip(),
                        ptype, lo, hi, v.get("duration"), v.get("duration"), s.get("description"), "booksy"))


# ---------------------------------------------------------------- GlossGenius
def glossgenius(db):
    sys.path.insert(0, str(HERE))
    from crawl_glossgenius import seeds
    for sub in seeds():
        url = f"https://{sub}.glossgenius.com/services"
        p = path_for("glossgenius", url)
        if not p.exists():
            continue
        h = gz(p)
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', h, re.S)
        if not m:
            continue
        s = m.group(1)
        d = json.loads(s)
        biz = find_key(d, "business_address_latitude")
        if not biz:
            continue
        lat, lng = biz.get("business_address_latitude"), biz.get("business_address_longitude")
        addr = biz.get("business_address") or ""
        if not in_metro(lat, lng, "MN" if re.search(r"\bMN\b|Minnesota", addr) else "XX"):
            continue
        bid = f"glossgenius:{sub}"
        city = (re.search(r",\s*([^,]+),\s*MN", addr) or [None, None])[1]
        users = (find_key(d, "users") or {}).get("users") or []
        members = [u for u in users if isinstance(u.get("services"), list) and u.get("online_visible", True)]
        db.execute("INSERT OR REPLACE INTO business VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            bid, None, "glossgenius", sub, f"https://{sub}.glossgenius.com/", biz.get("business_name"),
            addr, city, (re.findall(r"\b(5\d{4})\b", addr) or [None])[-1], lat, lng,
            "GlossGenius", None, int(bool(SUITE_RE.search(addr + " " + (biz.get("business_name") or "")))),
            None, None, SNAPSHOT))
        multi = len(members) > 1
        for mem in members:
            prov = None
            if multi:
                prov = f"{bid}:{mem.get('guid')}"
                db.execute("INSERT OR REPLACE INTO provider VALUES (?,?,?,?,?)",
                           (prov, bid, mem.get("full_name"), None, None))
            for sv in mem["services"]:
                if not isinstance(sv, dict) or "price" not in sv:
                    continue
                pr = sv.get("price")
                try:
                    pr = float(pr)
                except (TypeError, ValueError):
                    pr = None
                if sv.get("price_hidden") or pr is None:
                    ptype, lo, hi = "consult", None, None
                elif pr == 0:
                    ptype, lo, hi = "free", 0, 0
                elif sv.get("price_varies"):
                    ptype, lo, hi = "from", pr, None
                else:
                    ptype, lo, hi = "fixed", pr, pr
                dur = sv.get("total_duration")
                db.execute("INSERT OR REPLACE INTO service_listing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    f"{bid}:{sv.get('guid')}:{(mem.get('guid') or '')}", SNAPSHOT, bid, prov,
                    sv.get("category_name"), (sv.get("name") or "").strip(), "", ptype, lo, hi,
                    dur, dur, sv.get("description"), "glossgenius"))


def find_key(o, key):
    if isinstance(o, dict):
        if key in o:
            return o
        for v in o.values():
            r = find_key(v, key)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find_key(v, key)
            if r:
                return r
    return None


def find_all(o, key, pred, out=None):
    out = [] if out is None else out
    if isinstance(o, dict):
        if key in o and pred(o):
            out.append(o)
            return out
        for v in o.values():
            find_all(v, key, pred, out)
    elif isinstance(o, list):
        for v in o:
            find_all(v, key, pred, out)
    return out


# ---------------------------------------------------------------- venues
def norm_name(n):
    n = re.sub(r"[^a-z0-9 ]", " ", (n or "").lower())
    stop = {"the", "salon", "hair", "studio", "llc", "and", "co", "spa", "by", "barbershop", "barber", "shop"}
    return {w for w in n.split() if w not in stop and len(w) > 1}


def assign_venues(db):
    """Same shop on two platforms = within 150 m and sharing half its name words.
    Benchmarks count venues, never platform listings, so a shop is never counted twice."""
    rows = db.execute("SELECT business_id, name, lat, lng FROM business ORDER BY business_id").fetchall()
    venue = {}
    for i, (bid, name, lat, lng) in enumerate(rows):
        if bid in venue:
            continue
        venue[bid] = bid
        a = norm_name(name)
        for bid2, name2, lat2, lng2 in rows[i + 1:]:
            if bid2 in venue or bid2.split(":")[0] == bid.split(":")[0]:
                continue
            if miles(lat, lng, lat2, lng2) > 0.093:
                continue
            b = norm_name(name2)
            if a and b and len(a & b) / min(len(a), len(b)) >= 0.5:
                venue[bid2] = bid
    db.executemany("UPDATE business SET venue_id=? WHERE business_id=?", [(v, k) for k, v in venue.items()])


def main():
    if DB.exists():
        DB.unlink()
    db = sqlite3.connect(DB)
    db.executescript(DDL)
    fresha(db)
    booksy(db)
    glossgenius(db)
    from ownsite import load_into
    load_into(db)
    assign_venues(db)
    db.commit()
    for src, nb, nl in db.execute("""SELECT b.source, COUNT(DISTINCT b.business_id), COUNT(l.listing_id)
        FROM business b LEFT JOIN service_listing l USING(business_id) GROUP BY 1"""):
        print(f"{src:12} businesses {nb:5}  listings {nl:6}")
    print("venues", db.execute("SELECT COUNT(DISTINCT venue_id) FROM business").fetchone()[0])


if __name__ == "__main__":
    main()
