"""Canonical services and the rules that map a published service name onto one.

Rules, not a model: every mapping is reproducible and every miss is inspectable.
Order matters - the first rule whose `any` matches and whose `none` does not wins.
Text matched is lower-cased `name | variant | category`.

A listing that bundles two services ("cut + color", "balayage & haircut") maps to
nothing unless a combo code exists for it (cut_beard). Prices of bundles are not
base prices and would drag a median upward.
"""
import re

# code, family, plain label (what the page says), size modifier allowed
CODES = [
    ("cut_women", "hair", "Women's haircut"),
    ("cut_men", "hair", "Men's haircut"),
    ("cut_kids", "hair", "Kids' haircut"),
    ("fade", "barber", "Fade"),
    ("cut_beard", "barber", "Haircut + beard"),
    ("beard_trim", "barber", "Beard trim"),
    ("lineup", "barber", "Line up / edge up"),
    ("head_shave", "barber", "Head shave"),
    ("blowout", "hair", "Blowout"),
    ("silk_press", "hair", "Silk press"),
    ("updo", "hair", "Updo / special-event style"),
    ("color_single", "color", "All-over color"),
    ("color_root", "color", "Root touch-up"),
    ("highlight_partial", "color", "Partial highlights"),
    ("highlight_full", "color", "Full highlights"),
    ("balayage", "color", "Balayage"),
    ("toner_gloss", "color", "Toner / gloss"),
    ("bleach_tone", "color", "Bleach and tone"),
    ("keratin", "hair", "Keratin / smoothing"),
    ("perm", "hair", "Perm"),
    ("knotless", "braids", "Knotless braids"),
    ("box_braids", "braids", "Box braids"),
    ("cornrows", "braids", "Cornrows"),
    ("twists", "braids", "Twists"),
    ("loc_retwist", "braids", "Loc retwist"),
    ("starter_locs", "braids", "Starter locs"),
    ("sew_in", "braids", "Sew-in"),
    ("mani_classic", "nails", "Classic manicure"),
    ("mani_gel", "nails", "Gel manicure"),
    ("mani_structure", "nails", "Structure gel manicure"),
    ("pedi_classic", "nails", "Classic pedicure"),
    ("pedi_gel", "nails", "Gel pedicure"),
    ("acrylic_full", "nails", "Acrylic full set"),
    ("acrylic_fill", "nails", "Acrylic fill"),
    ("gelx_full", "nails", "Gel-X full set"),
    ("dip_powder", "nails", "Dip powder"),
    ("brow_wax", "brow_lash", "Brow wax"),
    ("brow_tint", "brow_lash", "Brow tint"),
    ("brow_lamination", "brow_lash", "Brow lamination"),
    ("lip_wax", "wax", "Lip wax"),
    ("brazilian_wax", "wax", "Brazilian wax"),
    ("lash_classic_full", "brow_lash", "Classic lash full set"),
    ("lash_hybrid_full", "brow_lash", "Hybrid lash full set"),
    ("lash_volume_full", "brow_lash", "Volume lash full set"),
    ("lash_fill", "brow_lash", "Lash fill"),
    ("lash_lift", "brow_lash", "Lash lift"),
    ("lash_tint", "brow_lash", "Lash tint"),
]
LABEL = {c: l for c, _, l in CODES}
FAMILY = {c: f for c, f, _ in CODES}

# Anything that makes a listing NOT a stand-alone base price.
NOT_BASE = re.compile(
    r"add[\s-]?on|\badd(ed)?\b|\bbangs?\b|fringe|neck trim|neck clean|face[\s-]?fram|addition|upgrade|removal|soak[\s-]?off|repair|correction|consult|"
    r"\bclass\b|course|training|certif|model|gift|deposit|package|membership|bundle|"
    r"\bmini\b|touch[\s-]?up only|redo|fix\b|tinsel|feathers|maintenance|"
    r"\bcopy of\b|house call|mobile|after[\s-]?hours?|sunday|holiday|vip|deluxe|luxury|ultimate|premium|"
    r"student|military|teacher|discount|special|promo|\bfree\b|take[\s-]?off|group home|practice|trial|"
    r"\bdesigns?\b|nail art|\bart\b|french|ombr[eé]|chrome|cat[\s-]?eye|pink (and|&) white|extendo|bridal|wedding")
SENIOR_CITIZEN = re.compile(r"senior(s)?\b(?!\s*(stylist|barber|artist|designer|level|colorist))|65\+|60\+|55\+|elder")
COMBO = re.compile(r"\+|&|\band\b|\bw/|\bwith\b|combo|package")

R = re.compile


def rule(code, any_, none=None, combo_ok=False):
    return (code, R(any_), R(none) if none else None, combo_ok)


RULES = [
    # lashes first: "full set" also appears on nails
    rule("lash_fill", r"\b(lash|lashes)\b.*\bfill|fill.*\blash|\brefill\b.*lash", r"brow"),
    rule("lash_volume_full", r"(mega[\s-]?)?volume.*(full set|set\b)|full set.*volume|volume lash", r"fill|hybrid|wispy hybrid|hair|tape|extension\b(?!s? lash)"),
    rule("lash_hybrid_full", r"hybrid.*(full set|set\b|lash|extension)|full set.*hybrid|^(light |wispy |cateye |cat eye )*hybrid$", r"fill|brow"),
    rule("lash_classic_full", r"classic.*(full set|lash)|full set.*classic|classic set", r"fill|manicure|pedicure|mani|pedi|massage|facial|cut|fade|wax|nail"),
    rule("lash_lift", r"lash lift|lash perm|keratin lash", r"brow"),
    rule("lash_tint", r"(lash|eyelash) tint", r"brow|lift"),
    rule("brow_lamination", r"brow lamination|lamination|brow lift", r"lash", combo_ok=True),
    rule("brow_tint", r"(brow|eyebrow) (tint|dye|stain)|tint.*brow", r"wax|lamination|lash|thread"),
    rule("brow_wax", r"(brow|eyebrow)s? (wax|shap|clean)|wax.*brow", r"tint|lamination|lip|chin|face|lash|dye"),
    rule("lip_wax", r"^(upper )?lip( wax)?\b|\blip wax|upper lip", r"brow|chin|face|blush|gloss|lash"),
    rule("brazilian_wax", r"brazilian(?! blow)", r"blowout|blow out|keratin|smooth|men|male|manzilian|bikini line"),
    # nails
    rule("mani_structure", r"structure(d)? gel|builder gel|bi?ab\b|gel overlay", r"pedi|fill|removal"),
    rule("gelx_full", r"gel[\s-]?x|apres", r"fill|removal|soak"),
    rule("acrylic_fill", r"acrylic.*(fill|refill)|fill.*acrylic|^fills?\b|^fill[\s-]?ins?\b", r"lash|brow"),
    rule("acrylic_full", r"acrylic.*(full set|set\b|nails?)|full set.*acrylic|^acrylic", r"fill|removal|toe|lash|pedi|repair"),
    rule("dip_powder", r"\bdip\b|dipping|sns", r"removal|pedi|toe"),
    rule("pedi_gel", r"(gel.*pedi|pedi.*gel)", r"kid|child|removal|mani|acrylic|russian|toes only"),
    rule("mani_gel", r"(gel.*mani|mani.*gel|gel polish manicure|shellac mani)", r"kid|child|removal|pedi|toe|feet|x\b|builder|structure|change|no gel|without gel|w/o gel"),
    rule("pedi_classic", r"pedicure", r"gel|kid|child|polish change|toe polish|add|acrylic|jelly|toes|mani|russian|medical"),
    rule("mani_classic", r"manicure", r"gel|kid|child|pedi|polish change|dip|structur|builder|single colou?r|acrylic|russian"),
    # braids and locs, size modifier read separately
    rule("knotless", r"knotless", r"removal|takedown|take down|kid|child|half|french|fulani|boho|bohemian|goddess|curl"),
    rule("box_braids", r"box braid", r"knotless|removal|takedown|take ?down|kid|child|half|boho|bohemian|goddess"),
    rule("cornrows", r"corn\s?rows?|feed[\s-]?in|stitch braid", r"kid|child|wig|removal"),
    rule("twists", r"(two|2)[\s-]?strand|senegalese|passion twist|\btwists?\b", r"loc|retwist|kid|child|removal|out\b"),
    rule("starter_locs", r"starter loc|start(ing)? loc|instant loc|comb coil", None),
    rule("loc_retwist", r"retwist|re-twist|loc maintenance|interlock", r"starter|instant|kid|child"),
    rule("sew_in", r"sew[\s-]?in|weave", r"removal|takedown|take down|wig|tape|extension|tighten|ponytail|half|crochet|braid|track"),
    # colour
    rule("balayage", r"balayage|foilyage|baby ?lights?|lived[\s-]?in", r"cut|toner only|gloss only|correction|add|\+|&", combo_ok=False),
    rule("highlight_full", r"full (foil|highlight)|full head (foil|highlight)|highlights? ?- ?full", r"cut|balayage|shave|loc|\+|&"),
    rule("highlight_partial", r"partial (foil|highlight)|half (head|foil)|highlights? ?- ?partial", r"cut|balayage|\+|&"),
    rule("color_root", r"root (touch|retouch|color|colour|refresh)|retouch|re-touch|regrowth", r"cut|\+|&|gloss|toner|bleach|lightener|highlight|foil|balayage|relax|perm|brow|beard"),
    rule("bleach_tone", r"bleach.*tone|on[\s-]?scalp", r"cut|\+(?! tone)|retouch|root"),
    rule("color_single", r"all[\s-]?over colou?r|single[\s-]?process|one[\s-]?colou?r|single colou?r|global colou?r|base colou?r|^colou?r$|^colou?r service", r"cut|\+|&|foil|highlight|balayage|correction|root|retouch|vivid|fashion|gloss|toner|eyebrow|brow|beard|kid"),
    rule("toner_gloss", r"^(toner|toning|gloss|glaze)|(toner|gloss|glaze)$|\bgloss\b|\btoner\b", r"cut|\+|&|blow|lip|nail|polish|highlight|balayage|foil"),
    rule("keratin", r"keratin|brazill?ian blow|smoothing|cezanne|express blowout", r"lash|\+|&|cut|extension|tip|bond|foot|feet"),
    rule("perm", r"\bperm\b|permanent wave|body wave|digital perm", r"lash|brow|makeup|cut|braid|relax|\+|&"),
    rule("silk_press", r"silk press", r"\+|&|cut|trim|kid|child"),
    rule("updo", r"\bup[\s-]?do\b|formal style|special occasion|event style", r"trial|makeup|practice|bridal|wedding|kid|child|\+|&"),
    rule("blowout", r"blow[\s-]?out|blow[\s-]?dry|wash (and|&|\+) style|shampoo (and|&|\+) style|wash (and|&) blow", r"cut|keratin|brazil|express blowout|color|colour|treatment|silk|extension"),
    # barber
    rule("cut_beard", r"(cut|fade|taper).*(beard)|(beard).*(cut|fade)", r"kid|child|senior", combo_ok=True),
    rule("head_shave", r"head shave|bald head|shave head|razor shave head|head shaving", r"beard|face"),
    rule("lineup", r"line[\s-]?up|edge[\s-]?up|shape[\s-]?up|lining", r"beard|cut|fade|kid"),
    rule("beard_trim", r"beard", r"cut|fade|dye|color|colour|shave head"),
    rule("fade", r"\bfade\b|taper|skin fade|bald fade|burst", r"kid|child|beard|senior|design"),
    # cuts
    rule("cut_kids", r"\b(kid|kids|child|children|children's|boys?|girls?|youth|junior|little|toddler|under \d+|\d+ ?(&|and) ?under)\b.*\b(cut|haircut|hair cut|trim)s?\b|\b(cut|haircut)s?\b.*\b(kid|kids|child|children|youth|boys?|girls?)\b", r"braid|loc|twist|knotless|press|spa|pedi|mani|nail|polish|wax|shampoo|bang|fringe|perm|color|colour"),
    rule("cut_men", r"\b(men'?s?|mens|male|gentlem[ae]n'?s?|guys?|boys?|gents?)\b.*\b(cut|haircut|hair cut|trim)|clipper cut|barber cut|short hair cut|short haircut|buzz", r"kid|child|women|ladies|beard|fade|braid|\+|&|color|colour"),
    rule("cut_women", r"\b(women'?s?|womens|ladies|ladys|female|woman)\b.*\b(cut|haircut|hair cut)", r"kid|child|men'?s cut|bang|fringe|\+|&|color|colour|foil|balayage|dry cut"),
    rule("cut_generic", r"^(wash,? )?(scissor cut|scissor haircut|wash,? cut,? (&|and|\+) style|wash (&|and|\+) cut|hair ?cut|haircut|hair cut|cut|adult haircut|adult cut|cut (&|and) style|haircut (&|and|\+) style|cut and blow ?dry|haircut (&|and|\+) blow ?dry|precision cut|signature cut|regular haircut|standard haircut|classic cut|classic haircut)s?$", None, combo_ok=True),
]

LENGTH = [("xl", r"extra[\s-]?long|x[\s-]?long|xl\b|waist|butt|hip length|super long|very long"),
          ("long", r"\blong\b|mid[\s-]?back|bra[\s-]?strap|past (the )?shoulder|thick"),
          ("medium", r"\bmedium length|\bmid[\s-]?length|shoulder length|\bmedium hair"),
          ("short", r"\bshort\b|chin length|pixie|above (the )?shoulder")]
SIZE = [("jumbo", r"jumbo|xl\b|extra large"), ("large", r"\blarge\b|\bbig\b"),
        ("smedium", r"smedium|small[\s/-]?medium|small[\s-]to[\s-]medium"),
        ("small", r"\bsmall\b|micro"), ("medium", r"\bmedium\b|\bmed\b")]
LASH_TYPE = [("mega", r"mega"), ("volume", r"volume"), ("hybrid", r"hybrid"), ("classic", r"classic")]
SIZE_CODES = {"knotless", "box_braids", "twists"}

# Stylist tiers: only when the word sits next to a role. "Senior" alone is a
# senior-citizen price on these menus (14 of 14 cases checked 2026-10-05).
ROLE = r"(stylist|stylilst|barber|artist|designer|colorist|educator)"
TIERS = [
    ("junior", r"\b(new talent|apprentice|emerging|rising star)\b|\b(junior|jr\.?|associate|level ?1|lvl ?1|tier ?1)\s*" + ROLE),
    ("master", r"\b(master|expert|elite|principal|level ?[45]|lvl ?[45]|tier ?[45])\s*" + ROLE),
    ("senior", r"\b(senior|sr\.?|advanced|lead|level ?3|lvl ?3|tier ?3)\s*" + ROLE),
    ("owner", r"\b(owner|creative director|artistic director|salon director)\b"),
    ("stylist", r"\b(level ?2|lvl ?2|tier ?2)\s*" + ROLE + r"|\bstaff stylist\b"),
]


def first(pairs, text):
    for key, pat in pairs:
        if re.search(pat, text):
            return key
    return None


def tier_of(text):
    for key, pat in TIERS:
        if re.search(pat, text):
            return key
    return None


def classify(name, variant, category):
    """-> (code, length_mod, size_mod, tier, is_base, why) ; code None when unmapped."""
    name_l = (name or "").lower().strip()
    var_l = (variant or "").lower().strip()
    cat_l = (category or "").lower().strip()
    text = f"{name_l} | {var_l}".strip(" |")
    tier = tier_of(f"{name_l} {var_l}") or tier_of(cat_l)
    code = None
    for c, any_, none, combo_ok in RULES:
        target = text
        if c.startswith("lash_") and "lash" not in text and "lash" in cat_l:
            target = f"{text} lash"
        if c in ("mani_classic", "pedi_classic") and not re.search(r"mani|pedi", text):
            continue
        hit = any_.search(name_l) or any_.search(target)
        if not hit:
            continue
        if none and none.search(text):
            continue
        bare = re.sub(r"bleach\s*(and|&|\+|,)\s*tone|(wash|shampoo)\s*(and|&|\+|,)?\s*(blow[\s-]?dry|blow[\s-]?out|style)|blow[\s-]?dry\s*(and|&|\+)\s*style|cut\s*(and|&|\+)\s*style", "one", name_l)
        bare = re.sub(r"\(.*?\)|\d+\s*(&|and|\+)\s*(under|up|older|younger|over)|(&|and) under|(&|and) up", "", bare)
        if not combo_ok and COMBO.search(bare) and c not in ("lash_fill",):
            # a bundle: two services sold as one price
            continue
        code = c
        break
    if code is None:
        return None, None, None, tier, 0, "no rule"
    length = first(LENGTH, text)
    size = first(SIZE, text) if code in SIZE_CODES else None
    if code == "lash_fill":
        size = first(LASH_TYPE, f"{text} {cat_l}")
    is_base = 1
    why = "rule"
    if NOT_BASE.search(name_l) or (var_l and NOT_BASE.search(var_l)):
        is_base, why = 0, "add-on/upgrade/special wording"
    elif SENIOR_CITIZEN.search(text) and tier is None:
        is_base, why = 0, "senior-citizen price"
    elif length in ("long", "xl") and code not in SIZE_CODES:
        is_base, why = 0, "length surcharge"
    return code, length, size, tier, is_base, why


def tier_from_column(s):
    """A price-table column header on a salon's own site is a stylist tier by
    construction. Named words win; bare level numbers map 1 junior, 2 stylist,
    3 senior, 4+ (incl. 4A/4AA) master."""
    s = (s or "").lower()
    if not s:
        return None
    if re.search(r"new talent|apprentice|emerging|junior|jr\b|associate|new artist", s):
        return "junior"
    if re.search(r"owner|director", s):
        return "owner"
    if re.search(r"master|expert|elite|principal|signature artist", s):
        return "master"
    if re.search(r"senior|sr\b|advanced|lead", s):
        return "senior"
    m = re.search(r"(level|lvl|tier|l)\s*(\d)", s)
    if m:
        n = int(m.group(2))
        return {1: "junior", 2: "stylist", 3: "senior"}.get(n, "master")
    if re.search(r"stylist|artist|designer|standard|staff", s):
        return "stylist"
    return None
