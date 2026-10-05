"""Discover and fetch every Twin Cities Fresha venue.

Seeds: every /lp/ landing page under us-minneapolis (business types, treatment types,
neighbourhoods; ~15 venues each). Then snowball: each in-metro venue page lists ~9
nearby venues. Venue pages are cached by fetch.get; parse_fresha.py reads the cache.
Writes pipeline/cache/fresha_venues.txt (in-metro slugs)."""
import json
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, CACHE  # noqa: E402
from geo import in_metro  # noqa: E402

BASE = "https://www.fresha.com"
LP_CAP = 60
LP_RE = re.compile(r'(/lp/en/(?:bt|tt)/[a-z0-9-]+/in/us-minneapolis(?:/[a-z0-9-]+)?)"')
VENUE_RE = re.compile(r'fresha\.com/a/([a-z0-9-]+)')


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def main():
    lp_seen, lp_q = set(), deque(["/lp/en/bt/hair-salons/in/us-minneapolis"])
    venues = set()
    while lp_q:
        lp = lp_q.popleft()
        if lp in lp_seen:
            continue
        lp_seen.add(lp)
        st, html = get("fresha_lp", BASE + lp)
        if st != 200:
            continue
        venues |= set(VENUE_RE.findall(html))
        for nxt in LP_RE.findall(html):
            # Root type pages first; neighbourhood pages only for the four core
            # business types. The full cross product is ~7,000 pages of repeats.
            if nxt in lp_seen:
                continue
            if nxt.endswith("/us-minneapolis"):
                lp_q.appendleft(nxt)
            elif re.search(r"/bt/(hair-salons|barbershops|nail-salons|eyebrows-and-lashes)/", nxt):
                lp_q.append(nxt)
        if len(lp_seen) >= LP_CAP:
            break
        if len(lp_seen) % 25 == 0:
            print(f"lp {len(lp_seen)} queued {len(lp_q)} venues {len(venues)}", flush=True)
    print(f"landing pages {len(lp_seen)}, venues {len(venues)}", flush=True)

    seen, q, metro = set(), deque(sorted(venues)), []
    while q:
        slug = q.popleft()
        if slug in seen:
            continue
        seen.add(slug)
        st, html = get("fresha", f"{BASE}/a/{slug}")
        d = next_data(html) if st == 200 else None
        try:
            data = d["props"]["pageProps"]["data"]
            a = data["location"]["address"]
        except (TypeError, KeyError):
            continue
        if not in_metro(a.get("latitude"), a.get("longitude"), a.get("region1")):
            continue
        metro.append(slug)
        try:
            for n in data["geolocation"]["nearbyLocations"]["locations"]:
                if n["slug"] not in seen:
                    q.append(n["slug"])
        except (TypeError, KeyError):
            pass
        if len(seen) % 50 == 0:
            print(f"venues fetched {len(seen)} metro {len(metro)} queued {len(q)}", flush=True)
    (CACHE / "fresha_venues.txt").write_text("\n".join(sorted(set(metro))) + "\n")
    print(f"DONE fetched {len(seen)} in-metro {len(set(metro))}")


if __name__ == "__main__":
    main()
