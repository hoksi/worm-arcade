"""Score evolved worms in the real Super Tank (MAME): 12 full games each, the same seeds for every worm (the seed sets
the start delay), 10 % sticky actions, until the last tank is lost. Needs a desktop MAME with Lua on PATH.

  python3 score_real.py out.json my_worm [other_run ...]      (runs are folders in ../worm/run)"""
import json, os, random, sys
from multiprocessing import Pool, current_process
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "worm"))
from tankenv import Env
import worm as W

KINDS = {"worm": W.WormPlayer, "free_io": W.FreeIOPlayer, "worm_freefire": W.WormFreeFirePlayer, "worm_line": W.WormLinePlayer,
         "free_freefire": W.FreeIOFreeFirePlayer, "free_line": W.FreeIOLinePlayer, "worm_split": W.WormSplitPlayer,
         "fake_freefire": W.WormFakeFreeFirePlayer, "fake2_freefire": W.WormFake2FreeFirePlayer,
         "worm_freefire_v2": W.WormFreeFireV2Player, "free_freefire_v2": W.FreeIOFreeFireV2Player}
RUN = os.path.join(HERE, "..", "worm", "run")
_env = None


def env():
    global _env
    if _env is None:
        _env = Env(9240 + current_process()._identity[0])
    return _env


def make(run):
    meta = json.load(open(f"{RUN}/{run}/meta.json"))
    cls = KINDS[meta.get("player") or ("free_io" if meta.get("free_io") else "worm")]
    return cls(None, np.load(f"{RUN}/{run}/best.npz")["theta"])


def game(args):
    run, seed = args
    e = env(); rs = random.Random(seed); pl = make(run)
    e.reboot(rs.randrange(1, 300)); o = e.reset(); last = (0, False); steps = fires = 0; done = False
    while not done and steps < 5000:
        a = pl.act(o)
        if rs.random() < 0.1:
            a = last
        last = a; fires += a[1]
        o, r, done, _ = e.step(*a); steps += 1
    return run, o["score"], steps, fires / steps


if __name__ == "__main__":
    out_path, runs = sys.argv[1], sys.argv[2:]
    with Pool(2) as p:
        res = p.map(game, [(r, 1000 + i) for i in range(12) for r in runs], chunksize=1)
    out = {}
    for r, s, n, f in res:
        out.setdefault(r, []).append((s, n, round(f, 3)))
    json.dump(out, open(out_path, "w"))
    for r, v in out.items():
        sc = np.array([x[0] for x in v])
        print(f"{r:16s} score {sc.mean():6.0f} ± {sc.std(ddof=1) / np.sqrt(len(sc)):4.0f} median {np.median(sc):6.0f} "
              f"range {sc.min()}-{sc.max()} | steps {np.mean([x[1] for x in v]):5.0f} | fire {np.mean([x[2] for x in v]):.2f}")
