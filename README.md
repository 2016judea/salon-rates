# Salon Prices · Twin Cities

**Live:** https://salon-rates.vercel.app

**Competitive Market Analysis.** What everyone in your sector is charging for a given service.

— Aidan, [*Business Prototypes*](https://randomaidan.substack.com/p/business-prototypes), 2026-10-12. Sibling instance of the same product: [PT rates](https://github.com/2016judea/pt-rates) (live at https://pt-rates.vercel.app). This one is the salon sector, where the price is each shop's own published menu.

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
- **"From $45" stays a starting price** and is shown with a "+"; a range shows as "$75–95".
  **Like with like:** a set price is compared only with set prices, a starting price only
  with other starting prices (this changed 15% of verdicts, 2026-10-13).
- **Try a price.** Open any row and type a price: it says where that price would land
  among the same shops. For a raise, a first price list, or a move to no-tip pricing.
- A shop whose own menu says its prices include the tip is marked as such.
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

## Distribution

[GO_TO_MARKET.md](GO_TO_MARKET.md): the ranked plays, the sales rules with their sources, and scored first-touch drafts. Nothing in it has been sent.

## Next build

The vision is *everyone in your sector*. Vagaro's shops are the gap in this one (robots.txt
blocks it), and each new sector is a new instance of the same product (PT rates is the first).

MIT licence.
