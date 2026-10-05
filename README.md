# Salon Prices · Twin Cities

**Live:** https://salon-rates.vercel.app

A phone-first page for a salon owner or stylist between clients: type your shop's
name and see, service by service, whether you charge more or less than shops like
yours nearby. *"Balayage: $75 under the middle price of 8 salons within 5 miles."*
Tap any row to see every shop it was compared against. Or flip to **A service**,
pick a service and a place, and see what shops there charge.

`grounded: 2026-10-05 — built the day Aidan named it, data model first, then the load, then the page`

## Where the prices come from

Every number is a shop's own published menu, read on the build date:

<!-- counts -->
| source | shops | menu lines |
|---|---|---|
| Booksy | 658 | 6,510 |
| GlossGenius | 152 | 4,197 |
| Fresha | 54 | 1,513 |
| Salons' own websites | 16 | 663 |

879 distinct shops after merging the same shop across platforms; 667 have at least one comparable price. 4,969 of 12,883 menu lines (39%) map to a canonical service. Built 2026-10-05.
<!-- /counts -->

Vagaro is not read: its robots.txt blocks every crawler not on its allowlist.

## How a comparison is made

The full model is in [SCHEMA.md](SCHEMA.md). In short:

- Every menu line is mapped to one of 47 services (`pipeline/taxonomy.py`) by rules,
  never by guesswork; bundles ("balayage + cut") are left out.
- Each shop contributes **one base price** per service: its cheapest stand-alone
  price at the shortest hair length it lists. Add-ons, deluxe versions, long-hair
  surcharges and senior-citizen prices are not base prices.
- **"From $45" stays a starting price** and is shown with a "+".
- **Stylist levels are never mixed.** A senior stylist's price is only compared with
  other senior stylists' prices.
- A comparison needs **at least 5 shops**. The page looks for them close first
  (3, 5, then 10 miles, same kind of shop first), then across the metro.

## Run it

```sh
python3 pipeline/crawl_fresha.py        # each crawler caches raw pages in pipeline/cache/
python3 pipeline/crawl_booksy.py        # MIN_GAP=3 if Booksy answers 429
python3 pipeline/crawl_glossgenius.py
python3 pipeline/ownsite.py             # menu transcription via `claude -p`, cached
pipeline/build.sh                       # load → map → benchmark → checks, from cache, ~10 s
VERCEL_TOKEN=... python3 scripts/deploy.py
```

`scripts/check.py` fails the build if a rule above is broken or a headline median
(men's cut, women's cut, balayage…) leaves the band a Twin Cities price actually sits in.

MIT licence.
