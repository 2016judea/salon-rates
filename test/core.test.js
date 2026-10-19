// node --test test/*.test.js
// salon_core.js is the one piece of arithmetic the page and /api/preview share.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const require = createRequire(import.meta.url);
const core = require("../site/salon_core.js");

const shop = (id, type, lat, lng, p) => ({ id, name: id, type, city: "Minneapolis", lat, lng, p });
// six barbershops within a mile of each other, all posting a set price for a men's cut
const near = (n) => Array.from({ length: n }, (_, i) => shop(`b${i}`, "barbershop", 44.97 + i * 0.001, -93.27, [["cut_men", "", "unknown", 20 + i * 5, 0, 30, null]]));

test("compare: fewer than MIN like-for-like peers is no answer, never a median of two", () => {
  const me = shop("me", "barbershop", 44.97, -93.27, [["cut_men", "", "unknown", 30, 0, 30, null]]);
  assert.equal(core.compare(near(3), me, me.p[0]), null);
  const c = core.compare(near(6), me, me.p[0]);
  assert.ok(c && c.n === 6);
  assert.equal(c.med, 32.5);
  // a starting price is never compared with set prices
  const from = { ...me, p: [["cut_men", "", "unknown", 30, 1, 30, null]] };
  assert.equal(core.compare(near(6), from, from.p[0]), null);
});

test("svcAnswer: an empty or thin group answers ok:false instead of NaN", () => {
  assert.deepEqual(core.svcAnswer([], "cut_men", "", "unknown", null, "metro"), { ok: false });
  assert.deepEqual(core.svcAnswer(near(4), "cut_men", "", "unknown", null, "metro"), { ok: false });
  const a = core.svcAnswer(near(5), "cut_men", "", "unknown", null, "metro");
  assert.ok(a.ok && a.nMain === 5 && !Number.isNaN(a.med) && a.otherMed === null);
});

test("q: the quantile of one value is that value", () => {
  assert.equal(core.q([42], 0.5), 42);
  assert.equal(core.q([10, 20], 0.5), 15);
});

// The "A service" pickers may only offer a size or stylist level that enough shops
// price, and the DEFAULT selection must be one of them. Lash fill (2026-10-18) had
// sizes [hybrid, volume] and no unsized shops, yet the page opened on "Any size not
// named" and said "Not enough shops list lash fill yet".
test("pickerOptions: the default size and level always have shops behind them", () => {
  const keys = { lash_fill: { sizes: ["hybrid", "volume"], tiers: ["unknown"] },
                 cut_women: { sizes: [""], tiers: ["unknown", "senior", "junior"] },
                 tiered_only: { sizes: [""], tiers: ["senior"] } };
  assert.deepEqual(core.pickerOptions(keys, "lash_fill"), { sizes: ["hybrid", "volume"], tiers: ["unknown"], size: "hybrid", tier: "unknown" });
  assert.deepEqual(core.pickerOptions(keys, "cut_women"), { sizes: [""], tiers: ["unknown", "senior", "junior"], size: "", tier: "unknown" });
  assert.equal(core.pickerOptions(keys, "tiered_only").tier, "senior");
  assert.deepEqual(core.pickerOptions(keys, "nope"), { sizes: [""], tiers: ["unknown"], size: "", tier: "unknown" });
  // and against the shipped lookup: every service's default is a key with shops
  const L = JSON.parse(readFileSync(new URL("../site/data/lookup.json", import.meta.url), "utf8"));
  for (const code of Object.keys(L.keys)) {
    const o = core.pickerOptions(L.keys, code);
    assert.ok(L.keys[code].sizes.includes(o.size) && L.keys[code].tiers.includes(o.tier), code);
  }
});
