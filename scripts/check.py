#!/usr/bin/env python3
"""Checks the built slices obey SCHEMA.md's rules and that the headline numbers are sane.
Run after pipeline/build.sh. Exits non-zero on the first broken rule."""
import json
import sys
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "site" / "data"
shops = json.loads((D / "shops.json").read_text())
bench = json.loads((D / "benchmarks.json").read_text())
meta = json.loads((D / "services.json").read_text())["meta"]
fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


# one base price per shop per (service, size, tier): a tier is never folded into another
keys = Counter((s["id"], p[0], p[1], p[2]) for s in shops for p in s["p"])
check(max(keys.values()) == 1, "one price per shop per service x size x tier")
check(all(b["n_shops"] >= meta["min_shops"] for b in bench), f"every published cell has >= {meta['min_shops']} shops")
check(all(p[3] >= 5 for s in shops for p in s["p"]), "no placeholder prices under $5")
check(all(b["p25"] <= b["median"] <= b["p75"] for b in bench), "p25 <= median <= p75 in every cell")


def metro(code, tier="unknown"):
    return next(b for b in bench if b["code"] == code and b["size"] == "" and b["geo"] == "metro"
                and b["type"] == "all" and b["tier"] == tier)


# Sanity bands: what a Twin Cities service actually costs (Great Clips ~$25 to
# downtown salons ~$100+). A median outside these means a mapping rule broke.
for code, lo, hi in [("cut_men", 25, 60), ("cut_women", 45, 95), ("cut_kids", 20, 45),
                     ("balayage", 130, 300), ("beard_trim", 12, 40), ("mani_gel", 30, 65),
                     ("brow_wax", 12, 35), ("color_root", 60, 140)]:
    m = metro(code)["median"]
    check(lo <= m <= hi, f"{code} metro median ${m:g} within ${lo}-${hi}")

if fails:
    sys.exit(1)
print(f"{len(shops)} shops, {len(bench)} cells, built {meta['built']}")
