/* salon_core.js — the comparison itself, shared by the page (once the full table is unlocked) and
   /api/preview (the free slice). Lifted unchanged from site/index.html, so a free answer and a paid
   answer are the same arithmetic. Works as a browser global (SalonCore) and as a CommonJS module. */
(function (root) {
  const MIN = 5;
  const RAD = [3, 5, 10];
  function miles(a, b) {
    const r = 3958.8, t = (x) => x * Math.PI / 180;
    const dLat = t(b.lat - a.lat), dLng = t(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(t(a.lat)) * Math.cos(t(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * r * Math.asin(Math.sqrt(h));
  }
  function q(xs, p) { const s = [...xs].sort((a, b) => a - b); const i = (s.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return s[lo] + (s[hi] - s[lo]) * (i - lo); }

  // every shop's price for one service key, with distance from a point.
  // from = a starting price ("from $X" or a range "$X–$Y"); top = the range's top, if any.
  function peers(SHOPS, code, size, tier, from, excludeId) {
    const out = [];
    for (const s of SHOPS) {
      if (s.id === excludeId) continue;
      for (const p of s.p) {
        if (p[0] === code && p[1] === size && p[2] === tier) { out.push({ shop: s, price: p[3], from: !!p[4], top: p[6] || null, d: from ? miles(from, s) : 0 }); break; }
      }
    }
    return out;
  }

  // the nearest group of at least MIN shops: same kind of shop first, then any kind.
  // Like with like: a set price is only compared with set prices, a starting price
  // ("from $X", "$X–$Y") only with other starting prices.
  function compare(SHOPS, shop, p) {
    const all = peers(SHOPS, p[0], p[1], p[2], shop, shop.id).filter((x) => x.from === !!p[4]);
    const steps = [["type", 3], ["type", 5], ["all", 3], ["type", 10], ["all", 5], ["all", 10], ["type", 99], ["all", 99]];
    for (const [scope, r] of steps) {
      const g = all.filter((x) => x.d <= r && (scope === "all" || x.shop.type === shop.type));
      if (g.length >= MIN) {
        const prices = g.map((x) => x.price).sort((a, b) => a - b);
        return { g, n: g.length, prices, r, scope, med: q(prices, .5), p25: q(prices, .25), p75: q(prices, .75), lo: prices[0], hi: prices[prices.length - 1] };
      }
    }
    return null;
  }

  // a group answers only if one kind of price (set, or starting) has MIN shops on its own
  const enough = (g) => g.filter((x) => !x.from).length >= MIN || g.filter((x) => x.from).length >= MIN;

  // "A service": what shops near a point charge for one service key. placeName is for the label.
  function svcAnswer(SHOPS, code, size, tier, pt, placeName) {
    let g = peers(SHOPS, code, size, tier, pt, null), label = "across the Twin Cities";
    if (pt) {
      let hit = null;
      for (const r of [...RAD, 20]) { const x = g.filter((y) => y.d <= r); if (enough(x)) { hit = [x, r]; break; } }
      if (hit) { g = hit[0]; label = `within ${hit[1]} miles of ${placeName}`; }
      else label = "across the Twin Cities (not enough nearby)";
    }
    if (!enough(g)) return { ok: false };
    const set = g.filter((x) => !x.from), start = g.filter((x) => x.from);
    const main = set.length >= MIN ? set : start, other = main === set ? start : set;
    const prices = main.map((x) => x.price);
    g.sort((a, b) => a.price - b.price);
    return {
      ok: true, label, n: g.length, nMain: main.length, starting: main === start,
      med: q(prices, .5), p25: q(prices, .25), p75: q(prices, .75),
      nOther: other.length, otherMed: other.length >= MIN ? q(other.map((x) => x.price), .5) : null,
      list: g,
    };
  }

  const api = { MIN, RAD, miles, q, peers, compare, enough, svcAnswer };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SalonCore = api;
})(this);
