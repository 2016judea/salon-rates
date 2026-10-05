"""Map every raw listing to a canonical service (listing_map), tag tiers, and set
each business's type. Reads/writes pipeline/salon.db. Prints coverage."""
import collections
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import classify, tier_of, tier_from_column, FAMILY  # noqa: E402

DB = Path(__file__).parent / "salon.db"

DDL = """
DROP TABLE IF EXISTS listing_map;
CREATE TABLE listing_map (
  listing_id TEXT PRIMARY KEY, code TEXT, length_mod TEXT, size_mod TEXT,
  tier TEXT, is_base INTEGER, method TEXT, confidence REAL, why TEXT
);
DROP TABLE IF EXISTS canonical_service;
CREATE TABLE canonical_service (code TEXT PRIMARY KEY, family TEXT, label TEXT);
"""

PLATFORM_TYPE = [
    ("barbershop", ("barber",)),
    ("nail", ("nail",)),
    ("lash_brow", ("brows", "lash", "eyebrow")),
    ("braiding", ("braid",)),
    ("salon", ("hair salon", "beauty salon", "hair")),
]


def main():
    db = sqlite3.connect(DB)
    db.executescript(DDL)
    from taxonomy import CODES
    db.executemany("INSERT INTO canonical_service VALUES (?,?,?)", CODES)

    # provider tiers from names like "Jess (Senior Stylist)"
    for pid, name in db.execute("SELECT provider_id, name FROM provider").fetchall():
        t = tier_of((name or "").lower())
        db.execute("UPDATE provider SET tier=?, tier_raw=? WHERE provider_id=?", (t or "unknown", name if t else None, pid))
    ptier = dict(db.execute("SELECT provider_id, tier FROM provider"))

    rows = db.execute("""SELECT l.listing_id, l.business_id, l.provider_id, l.name_raw, l.variant_raw,
                                l.category_raw, l.source FROM service_listing l""").fetchall()
    mapped = []
    fam_by_biz = collections.defaultdict(collections.Counter)
    for lid, bid, pid, name, var, cat, source in rows:
        if source == "own_site":
            # the variant slot holds the menu's tier column header
            code, length, size, tier, is_base, why = classify(name, "", cat)
            tier = tier_from_column(var) or tier
        else:
            code, length, size, tier, is_base, why = classify(name, var, cat)
        if tier is None and pid:
            tier = ptier.get(pid) if ptier.get(pid) != "unknown" else None
        mapped.append([lid, code, length, size, tier or "unknown", is_base, "rule", 0.9 if code else None, why, bid])
        if code:
            fam = FAMILY.get(code, "hair")
            if code == "cut_men":
                fam = "barber"
            fam_by_biz[bid][fam] += 1

    # business type: the menu decides, the platform category breaks ties
    btype = {}
    for bid, cat_raw, is_suite, nprov in db.execute("""SELECT b.business_id, b.category_raw, b.is_suite,
            (SELECT COUNT(*) FROM provider p WHERE p.business_id=b.business_id) FROM business b"""):
        c = fam_by_biz.get(bid, collections.Counter())
        total = sum(c.values())
        t = None
        if total >= 3:
            fam, n = c.most_common(1)[0]
            share = n / total
            if fam == "barber" and share >= 0.5:
                t = "barbershop"
            elif fam == "nails" and share >= 0.5:
                t = "nail"
            elif fam in ("brow_lash", "wax") and (c["brow_lash"] + c["wax"]) / total >= 0.5:
                t = "lash_brow"
            elif fam == "braids" and share >= 0.4:
                t = "braiding"
        if t is None:
            primary = (cat_raw or "").split("|")[0].lower()
            t = next((k for k, words in PLATFORM_TYPE if any(w in primary for w in words)), None)
        if t is None:
            t = "salon" if c["hair"] + c["color"] + c["barber"] else "other"
        if t == "salon" and (is_suite or (bid.startswith("glossgenius:") and nprov <= 1)):
            t = "suite"
        btype[bid] = t
    db.executemany("UPDATE business SET business_type=? WHERE business_id=?", [(v, k) for k, v in btype.items()])

    # A shop that names any stylist tier prices its unlabelled services as its
    # standard stylist, so those become "stylist", never blended with "unknown".
    tiered = {m[9] for m in mapped if m[4] not in ("unknown", None)}
    for m in mapped:
        if m[9] in tiered and m[4] == "unknown" and m[1]:
            m[4] = "stylist"
    # a bare "Haircut": men's at a barbershop, women's everywhere else
    for m in mapped:
        if m[1] == "cut_generic":
            m[1] = "cut_men" if btype.get(m[9]) == "barbershop" else "cut_women"
            m[7] = 0.7
            m[8] = "bare 'haircut' read by shop type"
    db.executemany("INSERT INTO listing_map VALUES (?,?,?,?,?,?,?,?,?)", [m[:9] for m in mapped])
    db.commit()

    n = len(mapped)
    k = sum(1 for m in mapped if m[1])
    kb = sum(1 for m in mapped if m[1] and m[5])
    print(f"listings {n}  mapped {k} ({k / n:.0%})  mapped+base {kb} ({kb / n:.0%})")
    print("types", collections.Counter(btype.values()).most_common())
    print("tiers", collections.Counter(m[4] for m in mapped if m[1]).most_common())


if __name__ == "__main__":
    main()
