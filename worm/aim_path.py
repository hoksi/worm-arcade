"""2026-11-03 (user: "확인하지 않은 1과2가 중요할것 같아. 확인해줘."), on the A no-firing-rule worm (pgx_freefire):
 1. pathway: does the mouth sense (I2) carry the aiming? (a) silence the I2 input in games -> aim index; also silence
    'predator ahead' (ASH). (b) probe at rest: inject I2 alone, watch spit (M1, pm3) and every other neuron; wiring paths
    I2 -> spit in the connectome; silence each strongly responding neuron and see how much of the spit response is left.
 2. turning to face: with the enemy beside, does the worm turn toward it (to bring it ahead) or away?
  aim_path.py pgx_freefire pgx_line_k100 pgx_fixed
"""
import os, json, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playground import Playground
import worm as W
CLS = {"worm_freefire": W.WormFreeFirePlayer, "worm_line": W.WormLinePlayer, "fake_freefire": W.WormFakeFreeFirePlayer,
       "fake2_freefire": W.WormFake2FreeFirePlayer, "free_freefire": W.FreeIOFreeFirePlayer, "free_line": W.FreeIOLinePlayer,
       "worm_freefire_v2": W.WormFreeFireV2Player, "free_freefire_v2": W.FreeIOFreeFireV2Player}
SHUF = None   # the wiring the probe uses (set from the run's player class: fake brains are shuffled)


def player(run, mute=()):
    meta = json.load(open(f"run/{run}/meta.json")); th = np.load(f"run/{run}/best.npz")["theta"]
    base = CLS.get(meta.get("player"), W.WormPlayer)

    class P(base):
        def senses(self, o):
            s = super().senses(o)
            self._raw = dict(s)
            for k in mute:
                if k in s: s[k] = 0.0
            return s
    return P(None, th), meta


def games(run, mute=(), n=12):
    probe = W.WormLinePlayer(None)
    on = [0, 0]; off = [0, 0]; kills = 0; score = 0
    tw = {"toward": 0, "away": 0}; side_steps = 0
    for seed in range(7000, 7000 + n):
        pl, meta = player(run, mute)
        pg = Playground(seed, max_steps=1500, predator=True, kill_pts=meta.get("kill_pts", 0), enemies=meta.get("enemies", 1), spawn=meta.get("spawn", "corner")); o = pg.reset()
        rs = random.Random(seed); last = (0, False); done = False
        while not done:
            h0 = pl.heading
            # where is the enemy relative to the worm before it acts
            side = None
            if o["player"] and o["enemies"]:
                hx, hy = W.HEADINGS[h0]; lx, ly = hy, -hx
                ex, ey = min(o["enemies"], key=lambda e: abs(e[0] - o["player"][0]) + abs(e[1] - o["player"][1]))
                dx, dy = ex - o["player"][0], ey - o["player"][1]
                fwd, sd = dx * hx + dy * hy, dx * lx + dy * ly
                if abs(sd) > abs(fwd) and abs(dx) + abs(dy) < 150:
                    side = "L" if sd > 0 else "R"
            a = pl.act(o)
            probe.heading = pl.heading
            ahead = probe.senses(o).get("mouth_noxious", 0) > 0
            if side:
                side_steps += 1
                dh = (pl.heading - h0) % 4
                if dh in (1, 3):
                    left_turn = dh == 3          # left turn = counter-clockwise = heading - 1
                    tw["toward" if left_turn == (side == "L") else "away"] += 1
            if rs.random() < 0.1: a = last
            last = a
            (on if ahead else off)[0] += a[1]; (on if ahead else off)[1] += 1
            o, r, done, _ = pg.step(*a)
        kills += pg.kills; score += pg.score
    return dict(fire_ahead=on[0] / max(on[1], 1), ahead_steps=on[1], fire_else=off[0] / max(off[1], 1), else_steps=off[1],
                kills=kills / n, score=score / n, side_steps=side_steps, **tw)


def probe_spit(theta, silence=None, steps=12, inp="mouth_noxious"):
    b = W.Brain(SHUF, theta)
    if silence is not None:
        out = b.out.copy(); out[silence] = 0; b.out = out; b._W = None
        G = b.G.copy(); G[silence, :] = 0; G[:, silence] = 0; b.G = G; b.Gdeg = G.sum(1)
    b.reset(); r = []; vs = []
    for _ in range(steps):
        m = b.step({inp: 1.0} if inp else {}); r.append(m["spit"]); vs.append(b.v.copy())
    return float(np.mean(r[-6:])), np.mean(vs[-6:], 0)


if __name__ == "__main__":
    runs = sys.argv[1:]
    ONLY_PROBE = bool(runs) and runs[0] == "--probe"
    if ONLY_PROBE: runs = runs[1:]
    print("== 1a. aim index with senses silenced (12 playground games)")
    for run in ([] if ONLY_PROBE else runs):
        for mute in [(), ("mouth_noxious",), ("pred_front",), ("mouth_noxious", "pred_front")]:
            r = games(run, mute)
            print(f"{run:14s} mute {'+'.join(mute) or 'none':24s} fire ahead {r['fire_ahead']:.2f} ({r['ahead_steps']}) else {r['fire_else']:.3f} | kills {r['kills']:.2f} score {r['score']:.0f}", flush=True)
            if run != runs[0]: break
    print("\n== 2. turning with the enemy beside (<150 px): toward vs away")
    for run in ([] if ONLY_PROBE else runs):
        r = games(run)
        t = r["toward"] + r["away"]
        print(f"{run:14s} side steps {r['side_steps']}, turns {t} ({t / max(r['side_steps'], 1):.2f}/step): toward {r['toward']} ({r['toward'] / max(t, 1):.0%}) away {r['away']}", flush=True)
    run = runs[0]
    th = np.load(f"run/{run}/best.npz")["theta"]
    SHUF = getattr(CLS.get(json.load(open(f"run/{run}/meta.json")).get("player"), W.WormPlayer), "SHUFFLE", None)
    b = W.Brain(SHUF, th); names = b.names
    print(f"\n== 1b. {run}: probe at rest, I2 alone")
    base, v_on = probe_spit(th)
    _, v_off = probe_spit(th, inp="smell_up")
    rest_spit, rest = probe_spit(th, inp=None)
    print(f"spit output: I2 on {base:.3f}, at rest {rest_spit:.3f}, threshold {b.readout[2]:.3f}")
    d = v_on - rest
    top = [i for i in np.argsort(-d) if d[i] > 0.05][:15]
    print("most raised by I2:", ", ".join(f"{names[i]} {d[i]:+.2f}" for i in top))
    low = [i for i in np.argsort(d) if d[i] < -0.05][:8]
    print("most lowered:", ", ".join(f"{names[i]} {d[i]:+.2f}" for i in low))
    # wiring: direct and 2-hop chemical/gap paths from I2 to spit
    C = (np.abs(b.C) > 0) | (b.G > 0)
    src = [b.idx[x] for x in ("I2L", "I2R")]; dst = b.M["spit"]
    direct = [(names[s], names[t]) for s in src for t in dst if C[t, s]]
    print("direct I2 -> spit synapses:", direct or "none")
    hop2 = {}
    for s in src:
        for m in np.where(C[:, s])[0]:
            for t in dst:
                if C[t, m]: hop2.setdefault(names[m], set()).add(names[t])
    print("I2 -> X -> spit:", {k: sorted(v) for k, v in hop2.items()})
    print("sign the evolved brain gives each (out = what the neuron sends, + excites / - inhibits):",
          {nm: round(float(b.out[b.idx[nm]]), 2) for nm in ["I2L", "I2R"] + sorted(hop2)[:10]})
    print("\nsilencing one neuron at a time (top responders + 2-hop relays): spit response left")
    cands = sorted(set(top) | {b.idx[k] for k in hop2})
    res = []
    for i in cands:
        if i in dst or names[i] in ("I2L", "I2R"): continue
        s, _ = probe_spit(th, silence=[i]); res.append((s, names[i]))
    for s, nm in sorted(res)[:10]:
        print(f"  silence {nm:6s} -> spit {s:.3f} ({s / base:.0%} of {base:.3f})")
