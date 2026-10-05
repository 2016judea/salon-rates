# Data model

`grounded: 2026-10-05 — designed before the first load, then corrected by it (notes marked "the data said")`

Built by `pipeline/` into `pipeline/salon.db` (SQLite, regenerated from the raw-page
cache, not committed). The site reads three JSON slices written from it.

```
crawl_*.py ─▶ pipeline/cache/ (raw pages, gzipped) ─▶ load.py ─▶ business, provider, service_listing
                                                   map_services.py ─▶ listing_map, canonical_service, business.business_type
                                                   benchmark.py ─▶ shop_price, benchmark ─▶ site/data/*.json
```

## Tables

### business — one row per shop per platform
| column | meaning |
|---|---|
| business_id | `<source>:<platform id>` (`fresha:1234`, `booksy:480334`, `glossgenius:<subdomain>`, `own_site:<host/path>`) |
| venue_id | the physical shop. Two platform rows within 150 m sharing half their name words are one venue. **Every count is of venues**, so a shop on Booksy and its own site is counted once. |
| source, source_id, url | where it was read |
| name, address, city, postal_code, lat, lng | as published; own-site addresses geocoded by the US Census geocoder |
| category_raw | the platform's own category words |
| business_type | `salon`, `barbershop`, `nail`, `lash_brow`, `braiding`, `suite` (an independent stylist: one-person GlossGenius book, or a Sola/Phenix/Salon Lofts-style suite), `other` (massage, med-spa). **The menu decides**: ≥50% of mapped services in one family sets the type; the platform category only breaks ties. |
| is_suite | address or name places it in a salon-suite building |
| rating, review_count, captured_at | |

### provider — a stylist, where the platform publishes per-person prices
`provider_id, business_id, name, tier_raw, tier`. Booksy variants tied to one staffer, and
GlossGenius multi-member books, carry their own prices.

### service_listing — the menu exactly as published (raw; never edited)
| column | meaning |
|---|---|
| listing_id, snapshot_date | primary key together. **Snapshots are kept**: re-running on a later day adds rows, so price history needs no schema change. |
| business_id, provider_id | provider null = the shop's price |
| category_raw, name_raw, variant_raw | as printed. On own sites `variant_raw` holds the price-table column header (the tier). |
| price_type | `fixed` · `from` ("From $X", "$X+") · `range` ("$X–$Y") · `consult` (no number) · `free` |
| price_min, price_max | `from` has no max. `range` keeps both. |
| duration_min/max, description, source | |

### canonical_service — the taxonomy (`pipeline/taxonomy.py`, 47 codes)
Hair: women's / men's / kids' cut, blowout, silk press, updo, keratin, perm.
Color: all-over, root touch-up, partial / full highlights, balayage, toner/gloss, bleach & tone.
Barber: fade, haircut + beard, beard trim, line-up, head shave.
Braids: knotless, box braids, twists (each by **size**: small · smedium · medium · large · jumbo), cornrows, loc retwist, starter locs, sew-in.
Nails: classic / gel / structure-gel manicure, classic / gel pedicure, acrylic full set / fill, Gel-X, dip.
Brow, lash, wax: brow wax / tint / lamination, lip wax, Brazilian, classic / hybrid / volume lash full set, lash fill (by lash **type**), lash lift, lash tint.

### listing_map — listing → canonical service
`listing_id, code, length_mod (short|medium|long|xl), size_mod, tier, is_base, method, confidence, why`.
Rules first, in order, first match wins; every miss is inspectable (`why`). A bundle
("balayage + cut") maps to nothing unless it is its own code (`cut_beard`). A bare
"Haircut" is a men's cut at a barbershop and a women's cut everywhere else (confidence 0.7).

### shop_price — one base price per venue × service × size × tier
The cheapest listing that is a stand-alone base service, at the shortest length the menu offers.

### benchmark — the published cells
`code, size_mod, geo_type (metro|city), geo_key, tier, business_type ('all' or one type),
n_shops, n_from, p25, median, p75, min, max, per_min_median, computed_at`.
Radius-from-a-point cells are computed in the browser from `shops.json` with the same rules.

## Rules the numbers obey

1. **Base price to base price.** Add-ons, upgrades, bundles, "deluxe/VIP/premium",
   new-client, holiday/after-hours, student/military/senior-citizen prices are never base.
2. **"From $X" is a floor and stays typed as one.** It contributes X; every cell
   carries `n_from`, and the page says "starting price" where it applies.
3. **Tiers are never blended.** Tier is part of every key. A menu that names any
   tier prices its unlabelled services as its standard `stylist`.
   *The data said:* "senior" on these menus is almost always a senior-citizen price
   (14 of 14 checked), so a tier needs a role word ("senior stylist"); "Level 1" alone
   is nail art or a peel. Booking platforms carry almost no tiered menus (1 shop of ~500);
   tiers come from salons' own sites, where numeric levels map 1 junior, 2 stylist,
   3 senior, 4+ master.
4. **Length surcharges are modifiers, not prices.** long / extra-long never count as base.
5. **Suppression.** A cell needs **5 distinct shops** or it is not published.
6. Prices under $5 are "ask me" placeholders ($0.01, $1) and are dropped.

## Sources

| source | how | notes |
|---|---|---|
| Fresha | venue pages' `__NEXT_DATA__` | discovery = landing pages + each venue's "nearby" list |
| Booksy | business pages' `__NUXT_DATA__` | discovery = Booksy's own US business sitemaps |
| GlossGenius | `<sub>.glossgenius.com/services` `__NEXT_DATA__` | no directory exists; subdomains from web search |
| Salons' own sites | page text → `claude -p` transcription → deterministic parse | the only real source of stylist tiers |
| Vagaro | **not used** | robots.txt blocks every crawler not on its allowlist |
| StyleSeat | not used | fully client-rendered |
