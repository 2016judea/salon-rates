"""Fetch candidate Twin Cities Booksy businesses from Booksy's own US business sitemaps.

Candidates: the Minneapolis metro bucket (city id 134619) plus any URL whose city slug is
a seven-county city name. Name collisions (Roseville CA, Bloomington IN...) are dropped
later on geo. Writes pipeline/cache/booksy_candidates.txt."""
import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, CACHE  # noqa: E402

CITIES = """minneapolis saint-paul st-paul edina richfield roseville maplewood brooklyn-park
brooklyn-center eden-prairie plymouth burnsville eagan woodbury coon-rapids blaine minnetonka
bloomington apple-valley lakeville shakopee savage maple-grove fridley columbia-heights
st-louis-park saint-louis-park hopkins inver-grove-heights south-st-paul west-st-paul
cottage-grove oakdale white-bear-lake new-brighton crystal robbinsdale golden-valley new-hope
champlin andover anoka ramsey chaska chanhassen prior-lake rosemount farmington hastings
stillwater shoreview arden-hills mounds-view spring-lake-park rogers wayzata excelsior mound
little-canada vadnais-heights north-st-paul lino-lakes ham-lake mendota-heights falcon-heights
lauderdale st-anthony osseo dayton corcoran medina orono victoria waconia jordan
belle-plaine forest-lake hugo lake-elmo north-branch""".split()


def main():
    urls = set()
    sm = CACHE / "booksy_sitemap"
    pat = re.compile(r"_(\d+)_([a-z-]+)$")
    for f in sm.glob("*.xml.gz"):
        for loc in re.findall(r"<loc>([^<]+)", gzip.decompress(f.read_bytes()).decode()):
            m = pat.search(loc)
            if m and (m.group(1) == "134619" or m.group(2) in CITIES):
                urls.add(loc)
    urls = sorted(urls)
    (CACHE / "booksy_candidates.txt").write_text("\n".join(urls) + "\n")
    print(f"candidates {len(urls)}", flush=True)
    ok = 0
    for i, u in enumerate(urls):
        st, _ = get("booksy", u)
        ok += st == 200
        if i % 50 == 0:
            print(f"{i}/{len(urls)} ok {ok}", flush=True)
    print(f"DONE {ok}/{len(urls)}")


if __name__ == "__main__":
    main()
