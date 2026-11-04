"""Report for the 2026-11-02 playground experiments (A pgx_fixed, B pgx_free, C, D, C+D, B+C+D): the best worm of each
run on the same 12 predator-playground games, plus the evolved translator of free-io runs (which neurons each sense
goes to, which nodes each action is read from).

  exp_report.py pgx_fixed pgx_free
"""
import os, json, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playground import Playground
from worm import (WormPlayer, FreeIOPlayer, ProprioPlayer, PlasticPlayer, PlasticEvoPlayer, WormSplitPlayer, WormFreeFirePlayer, WormLinePlayer, ProprioPlasticPlayer, FreeIOProprioPlasticPlayer, FreeIOFreeFirePlayer, FreeIOLinePlayer, WormFakeFreeFirePlayer, WormFake2FreeFirePlayer, WormFreeFireV2Player, FreeIOFreeFireV2Player,
                  ACTIONS)
KINDS = {"worm": WormPlayer, "free_io": FreeIOPlayer, "proprio": ProprioPlayer, "plastic": PlasticPlayer, "plastic_evo": PlasticEvoPlayer, "worm_split": WormSplitPlayer, "worm_freefire": WormFreeFirePlayer, "worm_line": WormLinePlayer, "free_freefire": FreeIOFreeFirePlayer, "free_line": FreeIOLinePlayer, "fake_freefire": WormFakeFreeFirePlayer, "fake2_freefire": WormFake2FreeFirePlayer, "worm_freefire_v2": WormFreeFireV2Player, "free_freefire_v2": FreeIOFreeFireV2Player,
         "proprio_plastic": ProprioPlasticPlayer, "free_proprio_plastic": FreeIOProprioPlasticPlayer}
RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run")


ENEMIES, SPAWN = 1, "corner"                    # set per run from meta.json (2026-11-03: two-enemy playground)


def load(run):
    global ENEMIES, SPAWN
    meta = json.load(open(f"{RUN}/{run}/meta.json")); z = np.load(f"{RUN}/{run}/best.npz")
    ENEMIES, SPAWN = meta.get("enemies", 1), meta.get("spawn", "corner")
    return KINDS[meta.get("player", "free_io" if meta.get("free_io") else "worm")], z["theta"], int(z["gen"])


def play(cls, theta, seed, steps=1500):
    rs = random.Random(seed); pl = cls(None, theta); pg = Playground(seed, max_steps=steps, predator=True, enemies=ENEMIES, spawn=SPAWN); o = pg.reset()
    last, done, halves = (0, False), False, [0, 0]
    while not done:
        a = pl.act(o)
        if rs.random() < 0.1:
            a = last
        last = a; before = pg.score
        o, r, done, _ = pg.step(*a)
        halves[pg.t > steps // 2] += pg.score - before
    return pg.score, pg.t, pg.deaths, pg.kills, halves[0], halves[1]


def translator(pl):
    out = {}
    for i, k in enumerate(pl.sense_keys):
        w = pl.Win[i]; order = np.argsort(-np.abs(w)); tot = np.abs(w).sum()
        out[k] = {"top": [(pl.in_groups[j], round(float(w[j]), 2)) for j in order[:4]],
                  "top3_share": round(float(np.abs(w[order[:3]]).sum() / tot), 2)}
    names = pl.brain.names
    for a_i, a in enumerate(ACTIONS):
        w = pl.Wout[a_i]; order = np.argsort(-np.abs(w)); tot = np.abs(w).sum()
        out["out_" + a] = {"top": [(names[pl.out_idx[j]], round(float(w[j]), 2)) for j in order[:5]],
                           "top5_share": round(float(np.abs(w[order[:5]]).sum() / tot), 2)}
    return out


if __name__ == "__main__":
    seeds = range(7000, 7012)
    rep = {}
    for run in sys.argv[1:]:
        cls, theta, gen = load(run)
        R = np.array([play(cls, theta, s) for s in seeds], float)
        rep[run] = {"gen": gen, "score": round(R[:, 0].mean()), "se": round(R[:, 0].std(ddof=1) / np.sqrt(len(R))),
                    "steps": round(R[:, 1].mean()), "deaths": round(R[:, 2].mean(), 2), "kills": round(R[:, 3].mean(), 2),
                    "first_half": round(R[:, 4].mean()), "second_half": round(R[:, 5].mean())}
        print(run, rep[run], flush=True)
        if hasattr(cls(None, theta), "Win"):
            rep[run]["translator"] = translator(cls(None, theta))
            for k, v in rep[run]["translator"].items():
                print("   ", k, v)
    json.dump(rep, open(f"{RUN}/exp_report_{'_'.join(sys.argv[1:])[:80]}.json", "w"), ensure_ascii=False, indent=1)
