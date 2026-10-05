"""Fetch the /services page of every GlossGenius seed subdomain (pipeline/glossgenius_seeds.txt).
GlossGenius has no public directory or business sitemap; seeds come from web search."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get  # noqa: E402

SEEDS = Path(__file__).parent / "glossgenius_seeds.txt"


def seeds():
    out = []
    for line in SEEDS.read_text().splitlines():
        if not line.startswith("#"):
            out += line.split()
    return sorted(set(out))


if __name__ == "__main__":
    s = seeds()
    ok = 0
    for i, sub in enumerate(s):
        st, _ = get("glossgenius", f"https://{sub}.glossgenius.com/services")
        ok += st == 200
    print(f"DONE {ok}/{len(s)}")
