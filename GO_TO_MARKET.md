# Go to market — Salon Prices

`grounded: 2026-10-13 — written the day the like-with-like iteration shipped, after the 10/05 batch (35 stylists, 0 replies) and the customer map (~/Desktop/customer-lab/maps/salon-rates.json)`

**The offer is visibility, not a sale.** The tool is free and carries no price
(distribution-channel rule 12: decide sale vs visibility before a batch; this one is
visibility). Nothing here has been sent. Every touch is a draft for Aidan to read.

## What we already know

| fact | source |
|---|---|
| 35 stylists + 1 suite manager emailed 10/05, opener "Your Haircut at $30, and $65 nearby". **0 replies**, 1 bounce | `bricks/data/outreach/salon_rates/tokens.csv` |
| That opener *did* quote their own menu. It then handed them a verdict about themselves and a link. Both agency yeses (Harford, Lakehaven) instead asked a question about the reader's own record that only the reader could answer | `distribution-channel` § What every yes had in common |
| Persona panels can't tell a good email from a bad one (AUC 0.51–0.54). A plain forecaster can (AUC 0.86, 5 positives) | `~/Desktop/panel-backtest/RESULTS.md` |
| Every segment in the map vouches through **fellow stylists**. Nobody in it cites a vendor or a directory | customer map, `vouchers` |
| 50 unsent GlossGenius menus publish both an email address and a starting price. 40 of them are independent stylists. Booksy (barbers, braiders) publishes no email | `site/data/shops.json` + the GlossGenius cache, counted 10/13 |
| 48 of 105 independent stylists charge less than the stylists near them on most of their services, compared like with like | same, counted 10/13 |

## The plays, ranked

Ranked by what vouches for us and how many stylists each reader stands in front of.
Plays 1 and 2 are super users (`distribution-channel` rule 2): one trust relationship
reaches many stylists. Play 3 is the only play that can reach the BUSINESS.md rule 4
floor on its own.

### 1. Beauty schools: whoever teaches "business practice"

- **Who vouches:** the school. A new graduate is the *New solo stylists* segment
  ("I am kind of lost on how I should price color services"; "a school-salon price
  does not carry over"). The school already decides what a student reads about money.
- **Their own record:** the Minnesota-required curriculum line in their own catalog or
  handbook. Aveda Arts & Sciences Institute Minneapolis prints *"instruction in business
  practice and in the Minnesota laws regulating those practices"* (handbook, published
  2022-07-01).
- **What they gain:** something concrete to hand a student on the day they ask what to charge.
- **List:** every cosmetology and esthiology school in the 7-county metro, with the named
  instructor or director for the business unit. Not built yet. **A row without a named
  person is not sendable** (`distribution-channel` procedure step 5).

### 2. Salon-suite owners (Sola, Phenix, Salon Lofts, MY Salon Suite, Salons by JC)

- **Who vouches:** the landlord. A Phenix building *"can hold anywhere from 30 to 60
  units"* (Jeni Schultz, twincities.com, 2023-06-14). Our data has 10 shops at Phenix
  Crystal alone (145 Willow Bend). Tenants are the *Stylists facing price pushback*
  segment: established, newly on their own.
- **Their own record:** their own words in local press, or their location page's tenant
  count ("100+ local professionals", Sola Northeast).
- **What they gain:** tenants who price to their market keep paying rent.
- **Already run:** 1 of 1 (Sola Northeast, 10/05), no reply. One send is a probe, not a
  result. Touch 2 goes to her only with a new record.

### 3. One stylist, one starting price, one question (carries the floor)

- **Who vouches:** their own menu line, quoted, plus a question only they can answer.
  This is the 10/05 batch with the verdict taken out and a question put in. It also
  uses what this iteration fixed: a "from $80" is now compared only with other
  starting prices.
- **Floor:** 50 *delivered* across at least 3 segments: independent stylists in
  Minneapolis and St. Paul, independent stylists in the suburbs, and salons, barbers,
  nail and braiding shops. The 35 already sent are not first touches.
- **Pipe:** Mailgun, at most 100 requests a rolling 24 h across every campaign. The
  Zoho mailbox is for replies.

**Not ranked: Reddit.** It is the map's voucher, but 0 of the 106 posts pulled were
about the Twin Cities. Our numbers answer only a Twin Cities stylist, so there is no
reader's record to open on yet.

## Rules for selling this product

Each rule carries its why and its source. They hold until a reply proves one wrong.

1. **Open on their record, then ask a question about it. Never hand them a verdict on
   it.** *Why:* "Your Haircut at $30, and $65 nearby" quoted their own menu and still got
   0 of 35. The yeses on record asked the reader something they already knew.
   (`tokens.csv`; `distribution-channel` § What every yes had in common.)
2. **Like with like, in every touch.** Quote a starting price only against other starting
   prices, and a set price only against set prices. *Why:* mixing the two changed 15% of
   verdicts (491 of 3,360, `SCHEMA.md` rule 2). A wrong number in line one costs the
   whole message.
3. **Every number comes from the day's build, never typed.** Rerun `pipeline/build.sh`,
   then derive each touch's numbers from `site/data/shops.json`. *Why:* the menus were read
   2026-10-05 and prices move. A typed figure already once made a bricks AI assert a false
   fact (bricks `CLAUDE.md`).
4. **Never call a no-tip shop "over".** Leave tip-inclusive menus out of any touch that
   compares price. *Why:* only 1 of 879 menus says its price includes the tip, so there is
   no fair group to compare it to (`SCHEMA.md`, Tip policy).
5. **Super users first. One channel per segment per fortnight. Three touches before
   silence counts.** *Why:* `distribution-channel` rules 2 and 5. The 10/05 batch got one touch.
6. **A verdict on the tool needs 50 delivered across 3 segments.** Fewer is a probe, and
   gets reported as one. *Why:* `~/.claude/BUSINESS.md` rule 4. 35 delivered to one segment
   was a probe.
7. **No price, no ask, no "free trial".** The tool is free; the touch says so in at most
   one line. *Why:* `distribution-channel` rules 10 and 12; bricks memory
   `feedback_price_is_negotiated_not_on_the_tool`.
8. **Each stylist's link is their own deep link** (`/#<shop id>`), so a quiet visit shows
   in PostHog. *Why:* silence in the inbox is not a no (`~/.claude/CLAUDE.md`, analytics).
9. **Score every draft before it sends** with the customer-lab screen, and rank drafts
   against each other, not against 50%. Never use a persona panel. *Why:* forecaster AUC
   0.86 vs personas ≈0.5 (`panel-backtest/RESULTS.md`). The prediction is logged first,
   so it is graded afterwards.

## First-touch drafts (DRAFTS: nothing sent)

Scored with `customer-lab/lab/screen.py` (forecaster-v1). The scores are logged to
`customer-lab/ledger/predictions.jsonl`. "Rank" is the share of our 417 past scored
sends this draft scores above.

### Play 1: beauty school (recipient not yet named): P(reply) 7%, P(click) 22%, rank 82%

> **Subject:** The "business practice" hours
>
> Hi,
>
> Your handbook says the cosmetology hours include "instruction in business practice and in the Minnesota laws regulating those practices."
>
> When a student asks what to charge once they leave the school salon, what do you point them to?
>
> I built a free page with the published menus of 667 Twin Cities shops, compared service by service. A student can pick a service and a city, or type a price and see where it would land: https://salon-rates.vercel.app
>
> Best,
> Aidan
> aidanjude.substack.com

To Aveda Arts & Sciences Institute Minneapolis. Find the named director before it sends.

### Play 2: Jeni Schultz, Phenix southwest metro (address not yet verified): P(reply) 6%, P(click) 22%, rank 65%

> **Subject:** Your tenants, "more established at a salon"
>
> Hi Jeni,
>
> In the June 2023 story on your Phenix plans, you said the people who rent a suite are usually "more established at a salon and want to move out into their own business with their clientele."
>
> The first thing that move asks of them is a price list. When a new tenant asks you what to charge, what do you tell them?
>
> I ask because I read the published menus of 105 independent stylists around the Twin Cities, and 48 of them charge less than the stylists near them on most of what they do. Any tenant can look themselves up by name: https://salon-rates.vercel.app
>
> Best,
> Aidan
> aidanjude.substack.com

The first version closed on "no reply needed" and asked her nothing. It scored 3% (rank 8%).
The same facts with a question about her tenants scored 6%. That is rule 1, measured on one draft.

### Play 3: Kelly Robbins, Bellina Hair Studio, Edina: P(reply) 4%, P(click) 17%, rank 22%

> **Subject:** Your Women's Haircut from $80
>
> Hi Kelly,
>
> Your GlossGenius menu lists Women's Haircut from $80. Nine independent stylists within 10 miles of you also post a starting price for a cut. Their middle is $65+.
>
> But a starting price is only half the number. When a cut is booked at $80, what does it usually come to by the end?
>
> I ask because I built a free page that compares starting prices only with other starting prices, never with a set price that is the whole bill: https://salon-rates.vercel.app/#glossgenius:bellinahairstudio
>
> Best,
> Aidan
> aidanjude.substack.com

The numbers are from the 2026-10-13 build: 9 peers, 7 of them start lower and 2 higher.
