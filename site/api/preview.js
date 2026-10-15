// GET /api/preview?shop=<id>   -> that shop's own prices against shops like it nearby, with the
//                                 middle price, the spread and the three nearest shops by name
// GET /api/preview?for=<token> -> the same, for the shop a /for/<token>/ page was made for
// GET /api/preview?svc=<code>&size=&tier=&place=<city|metro>|&lat=&lng=  -> one service's middle price
// The free slice. The same arithmetic as the paid page (../salon_core.js); only the list of every
// shop by name and price is held back for the full table (/api/data).
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const core = require("../salon_core.js");

const DIR = process.env.FULL_DIR || path.join(__dirname, "_full");
const SHOW = 3;
let SHOPS = null, FOR = null, PLACES = null;
function load() {
  SHOPS ??= JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(DIR, "full.json.gz"))));
  FOR ??= JSON.parse(fs.readFileSync(path.join(DIR, "for.json"), "utf8"));
  PLACES ??= JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "lookup.json"), "utf8")).cities;
}
const slim = (x) => ({ shop: { name: x.shop.name, city: x.shop.city, type: x.shop.type, nt: x.shop.nt || 0 }, price: x.price, from: x.from, top: x.top, d: x.d });

module.exports = (req, res) => {
  try { load(); } catch (e) { console.error("[preview] load:", e.message); return res.status(500).json({ error: "data not loaded" }); }
  res.setHeader("Cache-Control", "public, max-age=300");
  const qy = req.query;
  if (qy.svc) {
    const code = String(qy.svc), size = String(qy.size || ""), tier = String(qy.tier || "unknown"), place = String(qy.place || "metro");
    let pt = null, name = place;
    if (place === "here") { pt = { lat: Number(qy.lat), lng: Number(qy.lng) }; name = "you"; if (!isFinite(pt.lat) || !isFinite(pt.lng)) return res.status(400).json({ error: "bad point" }); }
    else if (place !== "metro") { pt = PLACES[place]; if (!pt) return res.status(404).json({ error: "no such place" }); }
    const a = core.svcAnswer(SHOPS, code, size, tier, pt, name);
    if (a.ok) { const near = pt ? [...a.list].sort((x, y) => x.d - y.d) : a.list; a.list = near.slice(0, SHOW).sort((x, y) => x.price - y.price).map(slim); }
    return res.status(200).json(a);
  }
  const token = String(qy.for || "");
  const id = token ? FOR[token] : String(qy.shop || "");
  const me = SHOPS.find((s) => s.id === id);
  if (!me) return res.status(404).json({ error: token ? "no such page" : "no such shop" });
  const rows = [];
  for (const p of me.p) {
    const c = core.compare(SHOPS, me, p);
    if (!c) continue;
    c.g = [...c.g].sort((a, b) => a.d - b.d).slice(0, SHOW).map(slim);
    rows.push({ p, c });
  }
  res.status(200).json({ shop: me.id, token: token || null, rows });
};
