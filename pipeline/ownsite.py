"""Salons' own websites: fetch the price page, let a model copy the menu out as
rows, parse prices deterministically, geocode the address, load as source 'own_site'.

The model only TRANSCRIBES (service text, tier text, price text exactly as printed);
it never classifies or normalises. Classification is taxonomy.py, same as every
other source. Extraction runs through `claude -p` on Aidan's subscription ($0)
and is cached per page, so re-running costs nothing.

Run: python3 pipeline/ownsite.py fills the extraction cache; load.py loads it.
"""
import gzip
import hashlib
import html as htmllib
import json
import re
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, path_for, CACHE  # noqa: E402
from geo import in_metro  # noqa: E402

HERE = Path(__file__).parent
DB = HERE / "salon.db"
SEEDS = HERE / "ownsite_seeds.txt"
XCACHE = CACHE / "ownsite_extract"
PRICE_LINK = re.compile(r'href="([^"#]+)"[^>]*>([^<]{0,60})<', re.I)

PROMPT = """Below is the visible text of a hair/beauty salon's web page.
Copy its price menu out as JSON. Transcribe; do not interpret or normalise.

Return ONLY a JSON object:
{"business_name": str, "street_address": str|null, "city": str|null, "state": str|null, "zip": str|null,
 "rows": [{"category": str|null, "service": str, "tier": str|null, "price": str, "duration": str|null}]}

- One row per (service, tier) price. If a table has columns per stylist level
  (e.g. "Level 1 | Level 2", "Senior | Master", "New Talent | Artist"), emit one row per
  column with the column header in "tier", copied exactly.
- "price" is the price text exactly as printed, e.g. "$65+", "$80-$95", "starting at $45", "45".
- No address on the page -> nulls. No prices on the page -> "rows": [].

PAGE TEXT:
"""


def visible_text(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|td|th)>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    h = htmllib.unescape(h)
    h = re.sub(r"[ \t\r\f\v]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def price_pages(url):
    """The seed page, plus up to 3 same-site pages whose link text says price/menu/services."""
    st, h = get("ownsite", url)
    if st != 200:
        return []
    pages = [(url, h)]
    host = urllib.parse.urlparse(url).netloc
    seen = {url}
    for href, label in PRICE_LINK.findall(h):
        full = urllib.parse.urljoin(url, href)
        if urllib.parse.urlparse(full).netloc != host or full in seen:
            continue
        if re.search(r"pric|menu|service|rates", href + " " + label, re.I) and not re.search(r"\.(jpg|png|pdf)$", full, re.I):
            seen.add(full)
            st2, h2 = get("ownsite", full)
            if st2 == 200:
                pages.append((full, h2))
        if len(pages) >= 4:
            break
    return pages


def extract(url, text):
    XCACHE.mkdir(parents=True, exist_ok=True)
    key = XCACHE / (hashlib.sha1((url + text).encode()).hexdigest() + ".json")
    if key.exists():
        return json.loads(key.read_text())
    out = subprocess.run(["claude", "-p", "--model", "sonnet", PROMPT + text[:60000]],
                         capture_output=True, text=True, timeout=600).stdout
    m = re.search(r"\{.*\}", out, re.S)
    try:
        data = json.loads(m.group(0)) if m else {"rows": []}
    except json.JSONDecodeError:
        data = {"rows": [], "error": out[:500]}
    key.write_text(json.dumps(data))
    return data


def geocode(addr):
    """US Census one-line geocoder: free, no key."""
    p = CACHE / "geocode" / (hashlib.sha1(addr.encode()).hexdigest() + ".json")
    if p.exists():
        return json.loads(p.read_text())
    q = urllib.parse.urlencode({"address": addr, "benchmark": "Public_AR_Current", "format": "json"})
    try:
        with urllib.request.urlopen(f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{q}", timeout=30) as r:
            d = json.loads(r.read())
        m = d["result"]["addressMatches"]
        res = {"lat": m[0]["coordinates"]["y"], "lng": m[0]["coordinates"]["x"]} if m else {}
    except Exception:
        res = {}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def parse_price(s):
    s = (s or "").lower()
    nums = [float(x.replace(",", "")) for x in re.findall(r"\$?\s*(\d[\d,]*(?:\.\d+)?)", s)]
    if not nums or re.search(r"consult|call|quote|ask|varies", s) and not nums:
        return "consult", None, None
    if re.search(r"\+|from|start|and up|& up|min", s):
        return "from", nums[0], None
    if len(nums) > 1 and re.search(r"-|–|to", s):
        return "range", nums[0], nums[-1]
    return "fixed", nums[0], nums[0]


def parse_minutes(s):
    if not s:
        return None
    s = s.lower()
    h = re.search(r"(\d+(?:\.\d+)?)\s*(h|hr|hour)", s)
    m = re.search(r"(\d+)\s*(m|min)", s)
    t = (float(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return int(t) or None


def load_into(db):
    kept = 0
    for url in [l.strip() for l in SEEDS.read_text().splitlines() if l.strip() and not l.startswith("#")]:
        rows, info = [], {}
        for purl, h in price_pages(url):
            d = extract(purl, visible_text(h))
            for k in ("business_name", "street_address", "city", "state", "zip"):
                info[k] = info.get(k) or d.get(k)
            rows += [dict(r, page=purl) for r in d.get("rows") or []]
        if not rows or not info.get("street_address"):
            print(f"  skip (no prices or no address): {url}")
            continue
        addr = ", ".join(x for x in (info["street_address"], info.get("city"), info.get("state"), info.get("zip")) if x)
        g = geocode(addr)
        if not in_metro(g.get("lat"), g.get("lng"), info.get("state") or "MN"):
            print(f"  skip (outside metro or not geocoded): {url} {addr}")
            continue
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        bid = f"own_site:{host}{urllib.parse.urlparse(url).path.rstrip('/')}"
        db.execute("INSERT OR REPLACE INTO business VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            bid, None, "own_site", host, url, info.get("business_name") or host, addr, info.get("city"),
            info.get("zip"), g["lat"], g["lng"], "Own website", None, 0, None, None,
            __import__("datetime").date.today().isoformat()))
        seen = set()
        for i, r in enumerate(rows):
            sig = (r.get("service"), r.get("tier"), r.get("price"))
            if sig in seen:
                continue
            seen.add(sig)
            ptype, lo, hi = parse_price(r.get("price"))
            dur = parse_minutes(r.get("duration"))
            db.execute("INSERT OR REPLACE INTO service_listing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                f"{bid}:{i}", __import__("datetime").date.today().isoformat(), bid, None, r.get("category"),
                (r.get("service") or "").strip(), (r.get("tier") or "").strip(), ptype, lo, hi, dur, dur,
                None, "own_site"))
        kept += 1
        print(f"  {info.get('business_name')}: {len(seen)} rows")
    print(f"own sites kept {kept}")


if __name__ == "__main__":
    # extraction only (fills the cache); load.py does the loading
    db = sqlite3.connect(":memory:")
    db.executescript(__import__("load").DDL)
    load_into(db)
