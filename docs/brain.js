// C. elegans connectome brain in plain JS (2026-11-03). Port of worm.py Brain.step:
//   v += 0.3 * (-v + relu(tanh(K * (W v) + bias + I - TH - ADAPT * u)));  u += 0.05 * (v - u)
//   W = C * out[source] + G - diag(rowsum G)
// float32 arithmetic (Math.fround) to follow numpy's float32. Works as an ES module and as a plain <script>.
const f = Math.fround;

class WormBrain {
  constructor(base, params) {
    this.base = base;
    this.names = base.names;
    this.n = base.names.length;
    this.idx = Object.fromEntries(base.names.map((nm, i) => [nm, i]));
    this.K = base.K; this.TH = base.TH; this.ADAPT = base.ADAPT; this.substeps = base.substeps;
    this.senses = base.senses; this.motors = base.motors;
    this.setParams(params);
    this.silenced = new Set();
    this.v = new Float32Array(this.n); this.u = new Float32Array(this.n);
    this._build();
  }

  setParams(p) {
    const n = this.n;
    this.params = p;
    this.out = Float32Array.from(p ? p.out : new Array(n).fill(1));
    this.bias = Float32Array.from(p ? p.bias : new Array(n).fill(0));
    this.readout = p ? p.readout.slice() : [0.02, 0.005, 0.3];
    this._W = null;
  }

  // silence = the neuron sends nothing and its gap junctions are cut (as aim_path.py probe_spit)
  silence(i, on = true) { on ? this.silenced.add(i) : this.silenced.delete(i); this._W = null; }

  _build() {
    const n = this.n, C = this.base.C, G = this.base.G, sil = this.silenced;
    // per target row: Map(source -> weight), summed in the same order as numpy's dense build
    const rows = Array.from({ length: n }, () => new Map());
    const add = (t, s, w) => rows[t].set(s, f((rows[t].get(s) || 0) + w));
    for (let k = 0; k < C.t.length; k++) {
      const s = C.s[k], out = sil.has(s) ? 0 : this.out[s];
      add(C.t[k], s, f(C.w[k] * out));
    }
    const gdeg = new Float32Array(n);
    for (let k = 0; k < G.t.length; k++) {
      const t = G.t[k], s = G.s[k];
      if (sil.has(t) || sil.has(s)) continue;
      add(t, s, G.w[k]);
      gdeg[t] = f(gdeg[t] + G.w[k]);
    }
    for (let t = 0; t < n; t++) if (gdeg[t]) add(t, t, -gdeg[t]);
    // CSR, columns ascending (scipy order)
    const ptr = new Int32Array(n + 1), col = [], val = [];
    for (let t = 0; t < n; t++) {
      for (const s of [...rows[t].keys()].sort((a, b) => a - b)) { const w = rows[t].get(s); if (w !== 0) { col.push(s); val.push(w); } }
      ptr[t + 1] = col.length;
    }
    this._W = { ptr, col: Int32Array.from(col), val: Float32Array.from(val) };
  }

  reset() { this.v.fill(0); this.u.fill(0); }

  // inputs: {sense_name: value} or a Float32Array of input currents (one per neuron)
  step(inputs = {}) {
    const n = this.n;
    if (!this._W) this._build();
    let I;
    if (inputs instanceof Float32Array) I = inputs;
    else {
      I = new Float32Array(n);
      for (const [k, val] of Object.entries(inputs)) for (const i of this.senses[k] || []) I[i] = f(I[i] + val);
    }
    const { ptr, col, val } = this._W, K = f(this.K), TH = f(this.TH), AD = f(this.ADAPT);
    const drive = new Float32Array(n), nv = new Float32Array(n);
    for (let s = 0; s < this.substeps; s++) {
      const a = this.v;
      for (let t = 0; t < n; t++) {
        let acc = 0;
        for (let k = ptr[t]; k < ptr[t + 1]; k++) acc = f(acc + f(val[k] * a[col[k]]));
        drive[t] = acc;
      }
      for (let t = 0; t < n; t++) {
        let x = f(f(f(f(f(K * drive[t]) + this.bias[t]) + I[t]) - TH) - f(AD * this.u[t]));
        x = f(Math.tanh(x));
        nv[t] = f(a[t] + f(f(0.3) * f(-a[t] + Math.max(0, x))));
      }
      for (let t = 0; t < n; t++) {         // a silenced neuron still computes, but W carries nothing from it
        this.u[t] = f(this.u[t] + f(f(0.05) * f(nv[t] - this.u[t])));
      }
      this.v.set(nv);
    }
    const m = {};
    for (const [k, ids] of Object.entries(this.motors)) {
      let acc = 0; for (const i of ids) acc += this.v[i]; m[k] = ids.length ? acc / ids.length : 0;
    }
    return m;
  }

  // the readout of worm.py act(): move / turn / fire decision from the motor pools
  decide(m) {
    const [thMove, thTurn, thFire] = this.readout;
    const move = m.fwd - m.back, turn = m.left - m.right;
    return {
      move: move > thMove ? "forward" : move < -thMove ? "back" : "stay",
      turn: Math.abs(turn) > thTurn ? (turn > 0 ? "left" : "right") : "none",
      fire: m.spit > thFire, move_v: move, turn_v: turn, spit_v: m.spit, th: { move: thMove, turn: thTurn, fire: thFire },
    };
  }
}

if (typeof module !== "undefined") module.exports = { WormBrain };
if (typeof window !== "undefined") window.WormBrain = WormBrain;
