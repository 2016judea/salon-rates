#!/usr/bin/env python3
"""Rewrite the counts table in README.md from pipeline/salon.db (run by build.sh)."""
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
db = sqlite3.connect(ROOT / "pipeline" / "salon.db")
NAMES = {"booksy": "Booksy", "glossgenius": "GlossGenius", "fresha": "Fresha", "own_site": "Salons' own websites"}
rows = db.execute("""SELECT b.source, COUNT(DISTINCT b.business_id), COUNT(l.listing_id)
                     FROM business b LEFT JOIN service_listing l USING(business_id) GROUP BY 1 ORDER BY 2 DESC""").fetchall()
venues = db.execute("SELECT COUNT(DISTINCT venue_id) FROM business").fetchone()[0]
priced = db.execute("SELECT COUNT(DISTINCT venue_id) FROM shop_price").fetchone()[0]
n, k = db.execute("SELECT COUNT(*), SUM(code IS NOT NULL) FROM listing_map").fetchone()
built = db.execute("SELECT MAX(computed_at) FROM benchmark").fetchone()[0]
table = ["| source | shops | menu lines |", "|---|---|---|"]
table += [f"| {NAMES.get(s, s)} | {b:,} | {l:,} |" for s, b, l in rows]
table.append(f"\n{venues:,} distinct shops after merging the same shop across platforms; {priced:,} have at least "
             f"one comparable price. {k:,} of {n:,} menu lines ({k / n:.0%}) map to a canonical service. Built {built}.")
p = ROOT / "README.md"
s = p.read_text()
s = re.sub(r"<!-- counts -->.*<!-- /counts -->", "<!-- counts -->\n" + "\n".join(table) + "\n<!-- /counts -->", s, flags=re.S)
p.write_text(s)
