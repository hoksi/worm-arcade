"""Export the worm brain for the browser (2026-11-03, user: "wsam 으로 변환해서 웹브라우져가 로딩후 js로 사용 가능하게
할 수 있을까?" -> plain JS, "ㅇㅇ 지금 시작해줘").

  base.json            public connectome (OpenWorm c302, Cook 2019, MIT): names, normalized C/G (sparse), sense/motor maps
  params/<run>.json    evolved knobs of one run, expanded per neuron: out, bias, readout thresholds
  test/<run>.json      a fixed input sequence + the Python brain's state after each step, for brain.test.mjs

Usage: export_web.py [run ...]   (default: pgx_freefire)"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "worm"))
import worm

HERE = os.path.dirname(os.path.abspath(__file__))
f32 = lambda x: [float(np.float32(v)) for v in x]


def sparse(M):
    t, s = np.nonzero(M)
    return {"t": t.tolist(), "s": s.tolist(), "w": f32(M[t, s])}


def base():
    b = worm.Brain()
    return {"source": "OpenWorm c302 herm_full_edgelist.csv (Cook et al. 2019), MIT", "names": b.names,
            "C": sparse(b.C), "G": sparse(b.G), "K": b.K, "TH": b.TH, "ADAPT": b.ADAPT, "substeps": b.substeps,
            "senses": {k: v for k, v in b.S.items()}, "motors": {k: v for k, v in b.M.items()},
            "group": b.group.tolist(), "gaba": sorted(worm.GABA)}


FREE = {"free_io", "free_freefire", "free_line", "free_freefire_v2", "free_proprio_plastic"}
def params(run):
    th = np.load(f"{HERE}/../worm/run/{run}/best.npz")["theta"]
    meta = json.load(open(f"{HERE}/../worm/run/{run}/meta.json"))
    kind = meta.get("player", "worm")
    cls = {"worm_freefire": worm.WormFreeFirePlayer, "worm_line": worm.WormLinePlayer, "free_freefire": worm.FreeIOFreeFirePlayer,
           "free_line": worm.FreeIOLinePlayer, "worm_freefire_v2": worm.WormFreeFireV2Player,
           "free_freefire_v2": worm.FreeIOFreeFireV2Player, "free_proprio_plastic": worm.FreeIOProprioPlasticPlayer,
           "proprio_plastic": worm.ProprioPlasticPlayer}.get(kind, worm.WormPlayer)
    pl = cls(None, th); b = pl.brain
    out = {"run": run, "player": kind, "gen": int(np.load(f"{HERE}/../worm/run/{run}/best.npz")["gen"]),
           "out": f32(b.out), "bias": f32(b.bias), "readout": f32(b.readout),
           # sense/fire rules of the player class (2026-11-03: browser play needs the same senses as training)
           "flags": {"NOXIOUS_OLD": bool(cls.NOXIOUS_OLD), "FIRE_GATE": bool(cls.FIRE_GATE), "PRED_SPLIT": bool(cls.PRED_SPLIT),
                     "SHELL_OLD": bool(getattr(cls, "SHELL_OLD", True))}}
    if hasattr(pl, "eta_group"):          # D: memory (reward-modulated plasticity on the existing synapses)
        out.update(plastic={"eta_group": f32(pl.eta_group), "decay": float(pl.decay), "forget": float(pl.forget), "pmax": float(pl.pmax)})
    if hasattr(pl, "_turn"):              # C: body feedback senses (prop_fwd / prop_back / prop_dorsal / prop_ventral)
        out.update(proprio=True, prop_senses={k: [int(i) for i in b.S[k]] for k in worm.PROPRIO})   # fixed wiring: where they go
    if kind in FREE:                       # B: evolved translator game senses -> sensory neurons, motor neurons -> actions
        out.update(free=True, sense_keys=list(pl.sense_keys), in_idx=pl.in_idx.tolist(), in_group=pl.in_group.tolist(),
                   out_idx=pl.out_idx.tolist(), Win=[f32(r) for r in pl.Win], Wout=[f32(r) for r in pl.Wout], actions=worm.ACTIONS)
    return b, out


def test_vectors(b, n=120, seed=0):
    rng = np.random.default_rng(seed)
    keys = list(worm.SENSORY)
    seq, vs, ms = [], [], []
    b.reset()
    for t in range(n):
        inp = {k: float(np.float32(rng.random() * 1.5)) for k in keys if rng.random() < 0.25}
        m = b.step(inp)
        seq.append(inp); vs.append(f32(b.v)); ms.append(m)
    return {"inputs": seq, "v": vs, "motors": ms}


if __name__ == "__main__":
    os.makedirs(f"{HERE}/params", exist_ok=True); os.makedirs(f"{HERE}/test", exist_ok=True)
    json.dump(base(), open(f"{HERE}/base.json", "w"), separators=(",", ":"))
    for run in sys.argv[1:] or ["pgx_freefire"]:
        b, p = params(run)
        json.dump(p, open(f"{HERE}/params/{run}.json", "w"), separators=(",", ":"))
        json.dump(test_vectors(b), open(f"{HERE}/test/{run}.json", "w"), separators=(",", ":"))
        print(run, p["player"], "gen", p["gen"])
    print("base.json", os.path.getsize(f"{HERE}/base.json") // 1024, "KB")
