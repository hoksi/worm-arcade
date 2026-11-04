// node play.test.cjs: JS parse/blocks/senses vs Python on frames captured from the server MAME (test/frames)
const fs = require("fs"); global.WormBrain = require("./brain.js").WormBrain;
const P = require("./play.js");
const base = JSON.parse(fs.readFileSync(__dirname + "/base.json"));
const params = JSON.parse(fs.readFileSync(__dirname + "/params/pgx_bfree_k200.json"));
const meta = JSON.parse(fs.readFileSync(__dirname + "/test/frames/meta.json"));
let bad = 0, maxd = 0;
const near = (a, b) => a.length === b.length && a.every((p, i) => Math.abs(p[0] - b[i][0]) < 1e-6 && Math.abs(p[1] - b[i][1]) < 1e-6);
for (const m of meta) {
  const raw = fs.readFileSync(`${__dirname}/test/frames/f${String(m.t).padStart(4, "0")}.bin`);
  const o = P.parse(raw, m.w, m.h, true);
  const pl = m.player, ok1 = (pl === null && o.player === null) || (pl && o.player && Math.abs(pl[0] - o.player[0]) < 1e-6 && Math.abs(pl[1] - o.player[1]) < 1e-6);
  const green = o.walls.reduce((a, b) => a + b, 0);
  const ok = ok1 && near(o.enemies, m.enemies) && near(o.mines, m.mines) && green === m.green;
  let sd = 0, nb = null;
  if (m.senses) {
    nb = P.blocks(o.walls, o.fw, o.fh).length;
    const w = new P.WormPlayerJS(base, params); w.heading = m.heading; w.sweep = m.sweep; w.last_smell = m.last_smell; o.shells = [];
    const s = w.senses(o);
    for (const k in m.senses) sd = Math.max(sd, Math.abs(m.senses[k] - (s[k] || 0)));
  }
  maxd = Math.max(maxd, sd);
  if (!ok || sd > 1e-9 || (nb !== null && nb !== m.blocks)) { bad++; console.log("MISMATCH t", m.t, { ok1, en: [o.enemies, m.enemies], mines: [o.mines.length, m.mines.length], green: [green, m.green], blocks: [nb, m.blocks], sd }); }
}
console.log(`${meta.length} frames, mismatches ${bad}, max sense diff ${maxd}`);
process.exit(bad ? 1 : 0);
