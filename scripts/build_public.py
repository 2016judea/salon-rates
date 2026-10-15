#!/usr/bin/env python3
"""Gate the data: site/ ships names and aggregates only; every shop's prices go to the paid route.

    python3 scripts/build_public.py        # last step of pipeline/build.sh

Reads private/shops.json (pipeline/benchmark.py, gitignored): every shop with its prices.

Writes:
  site/data/directory.json     every shop's name, city, kind and menu link, for the search box. No price.
  site/data/lookup.json        which sizes and stylist levels each service has enough shops for, and
                               each city's centre, so "A service" can offer its pickers
  private/bundle/full.json.gz  the full table: /api/data serves it behind the password, /api/preview
                               reads it to answer one shop's own row (or one service's middle price)
  private/bundle/for.json      {token: shop id} from outreach/round1/ledger.csv: /for/<token>/ opens
                               on the recipient's own shop without the list ever being public

scripts/deploy.py uploads private/bundle/ as api/_full/, readable by the functions only.
"""
import collections, csv, gzip, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV, DATA, BUNDLE = ROOT / "private", ROOT / "site" / "data", ROOT / "private" / "bundle"
LEDGER = ROOT / "outreach" / "round1" / "ledger.csv"
MIN = 5  # site/salon_core.js MIN
dump = lambda o: json.dumps(o, separators=(",", ":"))

shops = json.loads((PRIV / "shops.json").read_text())
directory = [{k: s[k] for k in ("id", "name", "city", "type", "url", "nt") if k in s} | {"n": len(s["p"])} for s in shops]
(DATA / "directory.json").write_text(dump(directory))

sizes, tiers = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
for s in shops:
    for p in s["p"]:
        sizes[p[0]][p[1]] += 1
        tiers[p[0]][p[2]] += 1
keys = {c: {"sizes": [k for k, n in sizes[c].items() if n >= MIN], "tiers": [k for k, n in tiers[c].items() if n >= MIN]} for c in sizes}
cities = collections.defaultdict(list)
for s in shops:
    if s.get("city"):
        cities[s["city"]].append(s)
places = {c: {"lat": sum(s["lat"] for s in v) / len(v), "lng": sum(s["lng"] for s in v) / len(v), "n": len(v)} for c, v in cities.items() if len(v) >= 3}
(DATA / "lookup.json").write_text(dump({"keys": keys, "cities": places}))

BUNDLE.mkdir(parents=True, exist_ok=True)
(BUNDLE / "full.json.gz").write_bytes(gzip.compress(dump(shops).encode(), 9))
ids = {s["id"] for s in shops}
tokens = {}
if LEDGER.exists():
    for r in csv.DictReader(LEDGER.open()):
        if r.get("token") and r.get("record_id") in ids:
            tokens[r["token"]] = r["record_id"]
(BUNDLE / "for.json").write_text(dump(tokens))
assert not (DATA / "shops.json").exists(), "site/data/shops.json must not exist: prices never ship statically"
print(f"directory {len(directory)} shops · lookup {len(keys)} services, {len(places)} places · {len(tokens)} /for/ tokens")
