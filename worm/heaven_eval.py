"""Heaven race (2026-11-03, user: "천국에서 학습 시키고 다 먹으면 종료. 그때의 걸음수를 기준으로 최상의 진화한 꼬마선충을
만들어보자"): no predator, food does not come back, the game ends when all 76 foods are eaten or after 1,500 steps.
For each run: how often it clears the field, the steps it takes, and how much it eats. 20 random starts (seeds 8000+),
10 % sticky actions. Reference: a planner that knows every food clears in ~300-345 steps (up/down/left/right).
  heaven_eval.py run [run ...]"""
import json, os, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playground import Playground
import worm as W
import aim_path as A
for run in sys.argv[1:]:
    meta = json.load(open(f"run/{run}/meta.json")) if os.path.exists(f"run/{run}/meta.json") else {}; th = np.load(f"run/{run}/best.npz")["theta"]
    cls = A.CLS.get(meta.get("player"), W.FreeIOPlayer if meta.get("free_io") else W.WormPlayer)
    steps, eaten, clears = [], [], 0
    for seed in range(8000, 8020):
        pg = Playground(seed, max_steps=1500, regrow=False); o = pg.reset(); pl = cls(None, th)
        rs = random.Random(seed); last = (0, False); done = False
        while not done:
            a = pl.act(o)
            if rs.random() < 0.1: a = last
            last = a; o, r, done, _ = pg.step(*a)
        clears += pg.cleared; eaten.append(len(pg.gone))
        if pg.cleared: steps.append(pg.t)
    print(f"{run:16s} cleared {clears}/20 | steps to clear {np.mean(steps) if steps else float('nan'):6.0f} (best {min(steps) if steps else '-'}) "
          f"| foods eaten {np.mean(eaten):5.1f}/76 | gen {int(np.load(f'run/{run}/best.npz')['gen'])}", flush=True)
