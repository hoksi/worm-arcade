// Super Tank screen -> worm senses -> evolved brain -> buttons, in the browser (2026-11-03).
// Ports of tankenv.py (the MAME frame reader) (parse, Env.observe shell split) and worm/worm.py (WormPlayer.senses /
// act, FreeIOPlayer.act). The browser MAME (0.285, -norotate, 256x256 canvas) draws exactly the server's raw frame,
// so the same thresholds apply. brain.js must be loaded first (WormBrain).
(function (root) {
  const FIELD = [32, 224, 10, 246];                  // y0, y1, x0, x1 on the clockwise-rotated screen
  const FW = 236, FH = 192;                           // FIELD_W, FIELD_H
  const HEADINGS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  const DIR_INDEX = { "0,-1": 1, "1,0": 3, "0,1": 5, "-1,0": 7 };
  const SENSES = ["smell_up", "smell_down", "pred_front", "pred_back", "pred_L", "pred_R", "touch_front", "touch_back",
    "touch_L", "touch_R", "nose", "mouth_food", "mouth_noxious"];

  // scipy.ndimage defaults: cross (4-neighbour) structure for both binary_dilation and label
  function dilate(m, w, h, it) {
    let a = m;
    for (let k = 0; k < it; k++) {
      const b = new Uint8Array(w * h);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (a[i] || (x > 0 && a[i - 1]) || (x < w - 1 && a[i + 1]) || (y > 0 && a[i - w]) || (y < h - 1 && a[i + w])) b[i] = 1;
      }
      a = b;
    }
    return a;
  }
  // connected components (4-neighbour) in scan order, like ndimage.label + find_objects: [{x0,x1,y0,y1,n}] (stop = max+1)
  function label(m, w, h) {
    const lab = new Int32Array(w * h), objs = [], stack = [];
    for (let i = 0; i < w * h; i++) {
      if (!m[i] || lab[i]) continue;
      const o = { x0: 1e9, x1: -1, y0: 1e9, y1: -1, n: 0, id: objs.length + 1 };
      lab[i] = o.id; stack.push(i);
      while (stack.length) {
        const j = stack.pop(), x = j % w, y = (j / w) | 0;
        o.n++; if (x < o.x0) o.x0 = x; if (x + 1 > o.x1) o.x1 = x + 1; if (y < o.y0) o.y0 = y; if (y + 1 > o.y1) o.y1 = y + 1;
        for (const k of [x > 0 ? j - 1 : -1, x < w - 1 ? j + 1 : -1, y > 0 ? j - w : -1, y < h - 1 ? j + w : -1])
          if (k >= 0 && m[k] && !lab[k]) { lab[k] = o.id; stack.push(k); }
      }
      objs.push(o);
    }
    return { lab, objs };
  }

  // tankenv.parse: raw pixels (RGBA, or BGRA with bgra=true) -> objects on the rotated playfield
  function parse(data, w, h, bgra) {
    const [y0, y1, x0, x1] = FIELD, fw = x1 - x0, fh = y1 - y0;
    const R = bgra ? 2 : 0, B = bgra ? 0 : 2;
    const yel = new Uint8Array(fw * fh), red = new Uint8Array(fw * fh), grn = new Uint8Array(fw * fh);
    let sx = 0, sy = 0, ny = 0;
    for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
      // np.rot90(a, k=-1): rotated[Y][X] = a[h-1-X][Y]
      const Y = y + y0, X = x + x0, src = ((h - 1 - X) * w + Y) * 4;
      const r = data[src + R], g = data[src + 1], b = data[src + B], i = y * fw + x;
      if (r > 150 && g > 150 && b < 100) { yel[i] = 1; sx += x; sy += y; ny++; }
      if (r > 150 && g < 80 && b < 80) red[i] = 1;
      if (g > 150 && r < 100) grn[i] = 1;
    }
    const out = { player: null, enemies: [], mines: [], walls: grn, fw, fh };
    if (ny > 15) out.player = [sx / ny, sy / ny];
    const { lab, objs } = label(dilate(red, fw, fh, 1), fw, fh);
    for (const o of objs) {
      let cnt = 0;                                     // (lab[sl] == i).sum(): this label's pixels inside its own box
      for (let y = o.y0; y < o.y1; y++) for (let x = o.x0; x < o.x1; x++) if (lab[y * fw + x] === o.id) cnt++;
      const c = [(o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2];
      (cnt > 40 ? out.enemies : out.mines).push(c);
    }
    return out;
  }

  // Player 2's sky-blue tank (2026-11-03, two-player mode): if the two tanks touch, both blow up, so the page hands it
  // to the worm as one more predator. Small cyan bits (player 2's shells) are left out, like mines among the red.
  function findP2(data, w, h, bgra) {
    const [y0, y1, x0, x1] = FIELD, fw = x1 - x0, fh = y1 - y0, R = bgra ? 2 : 0, B = bgra ? 0 : 2;
    const cy = new Uint8Array(fw * fh);
    for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
      const src = ((h - 1 - (x + x0)) * w + (y + y0)) * 4;
      if (data[src + R] < 100 && data[src + 1] > 150 && data[src + B] > 150) cy[y * fw + x] = 1;
    }
    const { lab, objs } = label(dilate(cy, fw, fh, 1), fw, fh), out = [];
    for (const o of objs) {
      let cnt = 0;
      for (let y = o.y0; y < o.y1; y++) for (let x = o.x0; x < o.x1; x++) if (lab[y * fw + x] === o.id) cnt++;
      if (cnt > 40) out.push([(o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2]);
    }
    return out;
  }

  // tankenv.Env.observe: a small red thing that was not there one step ago is a shell
  // Armour flash (2026-11-05, as tankenv.Env.observe): while armoured (after a red diamond, and in the grace after
  // (re)spawning) our tank blinks yellow/red, at most 2 red steps in a row. Read as colours, a red step lost the tank (the
  // worm stopped and reset its brain) and put an enemy on top of it. Now: no yellow tank, but a tank-sized red blob within
  // 10 px of where it was seen at most 3 steps ago -> that blob is our tank. A longer gap (explosion) is left as before.
  class Observer {
    constructor() { this.prev = []; this.seen = null; this.gap = 0; }
    observe(o) {
      if (!o.player && this.seen && this.gap < 3) {
        const lp = this.seen, d = e => Math.abs(e[0] - lp[0]) + Math.abs(e[1] - lp[1]), near = o.enemies.filter(e => d(e) < 10);
        if (near.length) { const me = near.reduce((a, b) => d(b) < d(a) ? b : a); o.player = me; o.enemies = o.enemies.filter(e => e !== me); o.flash = true; }
      }
      if (o.player && !o.flash) { this.seen = o.player; this.gap = 0; }
      else { this.gap++; if (o.flash) this.seen = o.player; }
      const near = m => this.prev.some(q => Math.abs(m[0] - q[0]) + Math.abs(m[1] - q[1]) < 1);
      o.shells = o.mines.filter(m => !near(m));
      o.mines = o.mines.filter(m => !o.shells.includes(m));
      this.prev = o.mines.concat(o.shells);
      return o;
    }
  }

  function blocks(walls, fw, fh) {
    const { objs } = label(dilate(walls, fw, fh, 2), fw, fh);
    return objs.map(o => [(o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2]);
  }
  const inside = (p, d, dist) => { const x = p[0] + d[0] * dist, y = p[1] + d[1] * dist; return (4 <= x && x < FW - 4 && 4 <= y && y < FH - 4) ? 1 : 0; };

  class WormPlayerJS {
    constructor(base, params) {
      this.p = params; this.flags = params.flags;
      this.brain = new WormBrain(base, params && params.out ? params : null);   // no values = the untrained brain
      this.heading = 0; this.turn_cd = 0; this.sweep = 1; this.last_smell = undefined; this.log = null;
      if (params.free) {
        this.Win = params.Win.map(r => Float32Array.from(r)); this.Wout = params.Wout.map(r => Float32Array.from(r));
        this.in_idx = params.in_idx; this.in_group = params.in_group; this.out_idx = params.out_idx;
      }
      this.proprio = !!params.proprio; this._pos = null; this._turn = 0;      // C: body feedback (worm.py ProprioPlayer)
      if (params.prop_senses) this.brain.senses = Object.assign({}, base.senses, params.prop_senses);   // fixed wiring: body-sense neurons
      this.plastic = params.plastic || null; this._score = null; this._reserve = null; this.reward_total = 0;   // D: memory
      if (this.plastic) this._initPlastic(base);
    }
    // worm.py PlasticPlayer: every existing synapse keeps an eligibility trace E of "pre and post on together"; eating (+1)
    // or being caught (-1) turns recent traces into lasting changes P (learning rate per neuron group of the target)
    _initPlastic(base) {
      const b = this.brain; b._build();
      const { ptr, val } = b._W, n = b.n, rows = new Int32Array(val.length);
      for (let t = 0; t < n; t++) for (let k = ptr[t]; k < ptr[t + 1]; k++) rows[k] = t;
      this.rows = rows; this.W0 = Float32Array.from(val); this.P = new Float32Array(val.length); this.E = new Float32Array(val.length);
      this.eta = Float32Array.from(rows, t => this.plastic.eta_group[base.group[t]]);
      this._Wref = b._W;
    }
    senses(o) {
      const p = o.player; if (!p) return {};
      const [hx, hy] = HEADINGS[this.heading], lx = hy, ly = -hx, [px, py] = p;
      const s = {}; for (const k of SENSES) s[k] = 0;
      this.sweep = -this.sweep;
      const head = [px + hx * 6 + lx * 3 * this.sweep, py + hy * 6 + ly * 3 * this.sweep];
      const foods = (o.food_xy ? o.food_xy : blocks(o.walls, o.fw, o.fh)).concat(o.mines);
      const near = foods.slice().sort((a, b) => (Math.abs(a[0] - head[0]) + Math.abs(a[1] - head[1])) - (Math.abs(b[0] - head[0]) + Math.abs(b[1] - head[1]))).slice(0, 3);
      let smell = 0; for (const [fx, fy] of near) smell += Math.exp(-(Math.abs(fx - head[0]) + Math.abs(fy - head[1])) / 40);
      const ds = smell - (this.last_smell === undefined ? smell : this.last_smell);
      this.last_smell = smell;
      s[ds > 0 ? "smell_up" : "smell_down"] = Math.min(Math.abs(ds) / (smell + 0.05) * 3, 1.0);
      for (const [fx, fy] of foods) {
        const dx = fx - px, dy = fy - py;
        if (Math.abs(dx * lx + dy * ly) < 6 && 0 < dx * hx + dy * hy && dx * hx + dy * hy < 24) { s.mouth_food = 1; break; }
      }
      for (const [ex, ey] of o.enemies) {
        const dx = ex - px, dy = ey - py, d = Math.abs(dx) + Math.abs(dy) + 1;
        const fwd = dx * hx + dy * hy, side = dx * lx + dy * ly;
        if (this.flags.PRED_SPLIT) {
          const tot = Math.abs(fwd) + Math.abs(side) + 1e-6;
          s[fwd > 0 ? "pred_front" : "pred_back"] += 3 * Math.exp(-d / 50) * Math.abs(fwd) / tot;
          s[side > 0 ? "pred_L" : "pred_R"] += 3 * Math.exp(-d / 50) * Math.abs(side) / tot;
        } else if (Math.abs(fwd) >= Math.abs(side)) s[fwd > 0 ? "pred_front" : "pred_back"] += 3 * Math.exp(-d / 50);
        else s[side > 0 ? "pred_L" : "pred_R"] += 3 * Math.exp(-d / 50);
        if (fwd > 0 && Math.abs(side) < 6) {
          if (!this.flags.NOXIOUS_OLD) s.mouth_noxious = 1;
          else if (d < 150 && clear(o.walls, o.fw, p, [ex, ey])) s.mouth_noxious = 1;
        }
      }
      const free_l = inside(p, [lx, ly], 10), free_r = inside(p, [-lx, -ly], 10);
      for (const [sx, sy] of o.shells || []) {
        const dx = sx - px, dy = sy - py;
        if (!this.flags.SHELL_OLD) {
          const fwd = dx * hx + dy * hy, side = dx * lx + dy * ly;
          if (Math.abs(side) < 8) s[fwd > 0 ? "touch_front" : "touch_back"] += 1.0;
          else if (Math.abs(fwd) < 8) s[side > 0 ? "touch_L" : "touch_R"] += 1.0;
          continue;
        }
        if ((Math.abs(dx) < 8 || Math.abs(dy) < 8) && Math.abs(dx) + Math.abs(dy) < 80) {
          s[dx * hx + dy * hy > 0 ? "touch_front" : "touch_back"] += 0.5;
          s[free_r >= free_l ? "touch_L" : "touch_R"] += 1.5;
        }
      }
      if (!free_l) s.touch_L += 0.7;
      if (!free_r) s.touch_R += 0.7;
      if (!inside(p, [hx, hy], 12)) s.nose = 1.0;
      if (this.extra) for (const k in this.extra) s[k] = (s[k] || 0) + this.extra[k];   // e.g. pain from a bite (lab)
      for (const k of ["pred_front", "pred_back", "pred_L", "pred_R"]) s[k] = Math.min(s[k], 2.0);
      if (this.proprio) {                              // what the body did on the last step
        if (this._pos) {
          const along = (p[0] - this._pos[0]) * hx + (p[1] - this._pos[1]) * hy;
          if (along > 1) s.prop_fwd = 0.5; else if (along < -1) s.prop_back = 0.5;
          if (this._turn === 3) s.prop_dorsal = 0.5; else if (this._turn === 1) s.prop_ventral = 0.5;
        }
        this._pos = p.slice();
      }
      return s;
    }
    // -> [dir index 0..8, fire]
    act(o) {
      if (!this.plastic) return this._act(o);
      const b = this.brain, f = Math.fround;
      if (!b._W || b._W !== this._Wref) { b._W = null; this._initPlastic({ group: b.base.group }); }   // rebuilt (a neuron silenced)
      let r = 0;
      if (this._score !== null) { r += ((o.score || 0) - this._score) / 50; if ((o.reserve || 0) < this._reserve) r -= 1; }
      this._score = o.score || 0; this._reserve = o.reserve || 0;
      const { P, E, eta, W0 } = this, val = b._W.val, pm = f(this.plastic.pmax), keep = f(1 - this.plastic.forget);
      if (r) {
        const fr = f(r);
        for (let k = 0; k < P.length; k++) P[k] = Math.min(pm, Math.max(-pm, f(P[k] + f(f(eta[k] * fr) * E[k]))));
        this.reward_total += r;
      }
      for (let k = 0; k < P.length; k++) { P[k] = f(P[k] * keep); val[k] = f(W0[k] + P[k]); }
      const a = this._act(o);
      const v = b.v, cols = b._W.col, dec = f(this.plastic.decay);
      for (let k = 0; k < E.length; k++) E[k] = f(f(dec * E[k]) + f(v[this.rows[k]] * v[cols[k]]));
      return a;
    }
    _act(o) {
      const h0 = this.heading, a = this._act1(o);
      this._turn = (this.heading - h0 + 4) % 4;
      return a;
    }
    _act1(o) {
      if (!o.player) { this.brain.reset(); this.heading = 0; return [0, false]; }
      const s = this.senses(o);
      let m;
      if (this.p.free) {
        const keys = this.p.sense_keys, G = this.Win[0].length, xg = new Float32Array(G);
        for (let k = 0; k < keys.length; k++) { const v = Math.fround(s[keys[k]] || 0); if (v) for (let g = 0; g < G; g++) xg[g] = Math.fround(xg[g] + Math.fround(v * this.Win[k][g])); }
        const I = new Float32Array(this.brain.n);
        for (let j = 0; j < this.in_idx.length; j++) I[this.in_idx[j]] = xg[this.in_group[j]];
        this.brain.step(I);
        m = {};
        this.p.actions.forEach((a, r) => { let acc = 0; for (let j = 0; j < this.out_idx.length; j++) acc += this.Wout[r][j] * this.brain.v[this.out_idx[j]]; m[a] = acc / this.out_idx.length * 10; });
      } else m = this.brain.step(s);
      const [thMove, thTurn, thFire] = this.brain.readout;
      const move = m.fwd - m.back, turn = m.left - m.right;
      const fire = m.spit > thFire && (!this.flags.FIRE_GATE || (s.mouth_noxious || 0) > 0);
      this.log = [s, m];
      const dirOf = () => DIR_INDEX[HEADINGS[this.heading].join(",")];
      if (this.turn_cd > 0) this.turn_cd--;
      else if (Math.abs(turn) > thTurn) { this.heading = (this.heading + (turn > 0 ? -1 : 1) + 4) % 4; this.turn_cd = 3; return [dirOf(), fire]; }
      if (move > thMove) return [dirOf(), fire];
      if (move < -thMove) { this.heading = (this.heading + 2) % 4; return [dirOf(), fire]; }
      return [0, fire];
    }
  }

  // worm._clear (only for players with NOXIOUS_OLD): no green between the worm and the enemy on the shared line
  function clear(walls, fw, p, e) {
    const x0 = p[0] | 0, y0 = p[1] | 0, x1 = e[0] | 0, y1 = e[1] | 0, at = (y, x) => walls[y * fw + x];
    if (Math.abs(x1 - x0) < 6) {
      const [lo, hi] = y0 < y1 ? [y0, y1] : [y1, y0];
      for (let y = lo; y < hi; y++) for (let x = Math.max(0, x0 - 2); x < x0 + 3; x++) if (at(y, x)) return false;
      return true;
    }
    const [lo, hi] = x0 < x1 ? [x0, x1] : [x1, x0];
    for (let y = Math.max(0, y0 - 2); y < y0 + 3; y++) for (let x = lo; x < hi; x++) if (at(y, x)) return false;
    return true;
  }

  const DIRS = { 0: [], 1: ["up"], 3: ["right"], 5: ["down"], 7: ["left"], 2: ["up", "right"], 4: ["down", "right"], 6: ["down", "left"], 8: ["up", "left"] };
  const api = { parse, findP2, Observer, blocks, WormPlayerJS, DIRS, SENSES };
  if (typeof module !== "undefined") module.exports = api;
  if (typeof window !== "undefined") window.WormPlay = api;
})(this);
