"""Aim index in the playground: fire rate when an enemy is straight ahead in line (mouth sense on, whole-line) vs not."""
import os, json, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playground import Playground
import worm as W
for run in sys.argv[1:]:
    meta = json.load(open(f"run/{run}/meta.json")); th = np.load(f"run/{run}/best.npz")["theta"]
    cls = {"worm_freefire": W.WormFreeFirePlayer, "worm_line": W.WormLinePlayer, "free_freefire": W.FreeIOFreeFirePlayer, "free_line": W.FreeIOLinePlayer, "fake_freefire": W.WormFakeFreeFirePlayer, "fake2_freefire": W.WormFake2FreeFirePlayer, "worm_freefire_v2": W.WormFreeFireV2Player, "free_freefire_v2": W.FreeIOFreeFireV2Player}.get(meta.get("player"), W.WormPlayer)
    probe = W.WormLinePlayer(None)          # whole-line mouth sense, used only to label "enemy ahead"
    on = [0, 0]; off = [0, 0]; kills = 0
    for seed in range(7000, 7012):
        pg = Playground(seed, max_steps=1500, predator=True, kill_pts=meta.get("kill_pts", 0), enemies=meta.get("enemies", 1), spawn=meta.get("spawn", "corner")); o = pg.reset()
        pl = cls(None, th); rs = random.Random(seed); last = (0, False); done = False
        while not done:
            a = pl.act(o)
            probe.heading = pl.heading
            ahead = probe.senses(o).get("mouth_noxious", 0) > 0
            if rs.random() < 0.1: a = last
            last = a
            (on if ahead else off)[0] += a[1]; (on if ahead else off)[1] += 1
            o, r, done, _ = pg.step(*a)
        kills += pg.kills
    print(f"{run:15s} fire when enemy ahead {on[0]/max(on[1],1):.2f} ({on[1]} steps) | otherwise {off[0]/max(off[1],1):.2f} ({off[1]} steps) | kills/game {kills/12:.2f}")
