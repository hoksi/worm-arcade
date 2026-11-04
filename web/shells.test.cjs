// node shells.test.cjs: the enemy-shell sense (old 80 px rule and the 2026-11-03 whole-line, side-aware rule) vs Python
const fs = require("fs"); global.WormBrain = require("./brain.js").WormBrain; const P = require("./play.js");
const base = JSON.parse(fs.readFileSync(__dirname + "/base.json"));
const T = JSON.parse(fs.readFileSync(__dirname + "/test/shells_v2.json"));
let worst = 0;
for (const c of T) {
  const w = new P.WormPlayerJS(base, { flags: { NOXIOUS_OLD: false, FIRE_GATE: false, PRED_SPLIT: false, SHELL_OLD: c.flag === "old" } });
  w.heading = c.h;
  const s = w.senses({ player: [100, 100], enemies: [[150, 60]], mines: [[110, 90]], walls: new Uint8Array(236 * 192), fw: 236, fh: 192, shells: c.shells });
  for (const k in c.s) worst = Math.max(worst, Math.abs(c.s[k] - (s[k] || 0)));
}
console.log(`${T.length} shell cases, max sense diff ${worst}`); process.exit(worst < 1e-9 ? 0 : 1);
