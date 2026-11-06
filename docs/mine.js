// Worms the visitor evolved in 선충 진화시키기 (2026-11-05, user: "홈페이지에서 내가 직접 진화시킨 탱크를 집어 넣을수 있도록").
// Reads the .db that page downloads (SQLite, read here with sql.js from catch-lib/; nothing is uploaded), picks up to 6
// worms (20-game-tested ones first, then the best of the last generation) and decodes their 1,595 genes exactly as
// worm.py Brain.set_params / FreeIOPlayer.set_theta do, onto the structure of the free-wiring worm pgx_bfree_k200.
// The chosen worms are kept in this browser's localStorage under "npc-mine" (shared with 선충 잡기, same format).
(function (root) {
  const KEY = "npc-mine", LIB = "catch-lib/";
  function decode(base, t, genes) {
    const f = Math.fround, G = Math.max(...base.group) + 1, n = base.group.length;
    const LO = [0.005, 0.001, 0.1], HI = [0.1, 0.03, 0.6], cl = (v, a, b) => Math.min(Math.max(v, a), b);
    const out = new Array(n), bias = new Array(n);
    for (let i = 0; i < n; i++) { const k = base.group[i]; out[i] = f(cl(1 + genes[k], -2, 2)); bias[i] = f(cl(0.5 * genes[G + k], -0.5, 0.5)); }
    const readout = [0, 1, 2].map(j => f(LO[j] + (HI[j] - LO[j]) * (1 + Math.tanh(genes[2 * G + j])) / 2));
    const nb = 2 * G + 3, R = t.Win.length, C = t.Win[0].length, R2 = t.Wout.length, C2 = t.Wout[0].length, Win = [], Wout = [];
    for (let r = 0; r < R; r++) Win.push(Array.from(genes.subarray(nb + r * C, nb + (r + 1) * C)));
    for (let r = 0; r < R2; r++) Wout.push(Array.from(genes.subarray(nb + R * C + r * C2, nb + R * C + (r + 1) * C2)));
    return Object.assign({}, t, { out, bias, readout, Win, Wout, run: "evolve", gen: 0 });
  }
  async function sqljs() {
    if (!root.initSqlJs) await new Promise((ok, bad) => { const s = document.createElement("script"); s.src = LIB + "sql-wasm.js"; s.onload = ok; s.onerror = () => bad(new Error("sql.js")); document.head.append(s); });
    return root.initSqlJs({ locateFile: f => LIB + f });
  }
  async function read(file) {
    const SQL = await sqljs(), db = new SQL.Database(new Uint8Array(await file.arrayBuffer()));
    const q = (sql, p = []) => { const st = db.prepare(sql); st.bind(p); const r = []; while (st.step()) r.push(st.getAsObject()); st.free(); return r; };
    let meta = {}, rows = [];
    try { meta = Object.fromEntries(q("SELECT key, value FROM meta").map(r => [r.key, r.value])); } catch (e) { db.close(); throw new Error("not an evolve file"); }
    try { rows = q("SELECT t.worm id, w.name, w.gen, t.mean score, 'test' kind FROM tests t JOIN worms w ON w.id=t.worm ORDER BY t.mean DESC LIMIT 6"); } catch (e) {}
    if (rows.length < 6) {
      const g = (q("SELECT MAX(game) g FROM plays")[0] || {}).g, have = new Set(rows.map(r => r.id));
      if (g != null) rows = rows.concat(q("SELECT w.id, w.name, w.gen, AVG(p.score) score, 'gen' kind FROM worms w JOIN plays p ON p.worm=w.id AND p.game=? GROUP BY w.id ORDER BY score DESC", [g]).filter(r => !have.has(r.id))).slice(0, 6);
    }
    const worms = rows.map(r => { const b = q("SELECT genes FROM worms WHERE id=?", [r.id])[0].genes;
      return { name: r.name, gen: r.gen, score: r.score, kind: r.kind, genes: new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)) }; });
    db.close();
    if (!worms.length || worms.some(w => w.genes.length !== 1595)) throw new Error("not an evolve file");
    return { file: file.name, stage: meta.stage, worms };
  }
  const enc = u8 => { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  function save(set) { try { localStorage.setItem(KEY, JSON.stringify(Object.assign({}, set, { worms: set.worms.map(w => Object.assign({}, w, { genes: enc(new Uint8Array(w.genes.buffer)) })) }))); } catch (e) {} }
  function restore() {
    try { const t = localStorage.getItem(KEY); if (!t) return null; const set = JSON.parse(t);
      set.worms.forEach(w => { w.genes = new Float32Array(Uint8Array.from(atob(w.genes), c => c.charCodeAt(0)).buffer); }); return set; } catch (e) { return null; }
  }
  root.Mine = { decode, read, save, restore };
})(typeof window !== "undefined" ? window : this);
