"""Evolve worms in the playground (playground.py): food everywhere, no predators (2026-11-01, user: "놀이터에서 수천세대
학습된 선충의 모습을 보고 싶어"). Same brain, senses, readout and GA as worm_evolve.py; the worms start from the raw
connectome (generation 0), not from the Super Tank runs, so these are worms raised in the playground only.
Fitness = food score over EPISODES games of STEPS steps from random starts, 10 % sticky actions.
2026-11-02 (user): --sym ties left-right pairs; food grows back only when the whole field is eaten.

  pg_evolve.py --gens 5000            (resumes from run/pg/state.npz; best.npz is what the spectator shows)
"""
import argparse, csv, os, random, sys, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playground import Playground
from worm import WormFreeFireV2Player, FreeIOFreeFireV2Player, WormPlayer, WormSplitPlayer, WormFreeFirePlayer, WormLinePlayer, Brain, FreeIOPlayer, ProprioPlayer, PlasticPlayer, PlasticEvoPlayer, ProprioPlasticPlayer, FreeIOProprioPlasticPlayer, FreeIOFreeFirePlayer, FreeIOLinePlayer, WormFakeFreeFirePlayer, WormFake2FreeFirePlayer

RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run")


PREDATOR, FREE_IO, KIND, KILL_PTS, ENEMIES = False, False, "worm", 0, 1
REGROW, CLEAR_BONUS = True, 0
SPAWN = "corner"
PLAYERS = {"worm": WormPlayer, "free_io": FreeIOPlayer, "proprio": ProprioPlayer, "plastic": PlasticPlayer, "plastic_evo": PlasticEvoPlayer, "proprio_plastic": ProprioPlasticPlayer,
           "free_proprio_plastic": FreeIOProprioPlasticPlayer, "worm_split": WormSplitPlayer, "worm_freefire": WormFreeFirePlayer, "worm_line": WormLinePlayer, "free_freefire": FreeIOFreeFirePlayer, "free_line": FreeIOLinePlayer, "fake_freefire": WormFakeFreeFirePlayer, "fake2_freefire": WormFake2FreeFirePlayer, "worm_freefire_v2": WormFreeFireV2Player, "free_freefire_v2": FreeIOFreeFireV2Player}   # --predator (2026-11-02): one enemy tank in the playground


def play(theta, seed, steps, sticky=0.1):
    rs = random.Random(seed)
    pg = Playground(seed, max_steps=steps, predator=PREDATOR, kill_pts=KILL_PTS, enemies=ENEMIES, regrow=REGROW, spawn=SPAWN); o = pg.reset()
    pl = PLAYERS[KIND](None, theta); last = (0, False); done = False
    while not done:
        a = pl.act(o)
        if rs.random() < sticky:
            a = last
        last = a
        o, r, done, _ = pg.step(*a)
    # heaven race (2026-11-03): clearing the field early earns CLEAR_BONUS points per step left
    return pg.score + (CLEAR_BONUS * (steps - pg.t) if pg.cleared else 0)


def write_web_json(run, out):
    """Next to best.npz, the same brain for the browser pages (2026-11-03, user: "모델 데이타를 json으로도 쓰도록 하면 변환
    필요 없이 바로 올릴 수 있겠네"): the format of web/export_web.py, so it can go straight into the pages' models/ folder.
    A failure here is logged and never stops training."""
    try:
        import importlib.util, json as _json
        spec = importlib.util.spec_from_file_location("export_web", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "export_web.py"))
        ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
        _, data = ex.params(run)
        tmp = f"{out}/best.web.json.tmp"
        with open(tmp, "w") as f:
            _json.dump(data, f, separators=(",", ":"))
        os.replace(tmp, f"{out}/best.web.json")
    except Exception as e:                    # noqa: BLE001 - the browser copy must never break a training run
        print(f"[pg] web json not written: {e!r}", flush=True)


def evaluate(args):
    theta, seeds, steps = args
    return float(np.mean([play(theta, s, steps) for s in seeds]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=5000); ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--elite", type=int, default=6); ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--steps", type=int, default=800); ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--sigma", type=float, default=0.1); ap.add_argument("--out", default="pg")
    ap.add_argument("--sym", action="store_true", help="left-right pairs share their parameters (2026-11-02)")
    ap.add_argument("--kill-pts", type=int, default=0, help="score for hitting the enemy (real game: 100; 2026-11-03)")
    ap.add_argument("--predator", action="store_true", help="one enemy tank, 3 lives (2026-11-02)")
    ap.add_argument("--enemies", type=int, default=1, help="2: a second enemy joins after 300-370 steps, as in the game (2026-11-03)")
    ap.add_argument("--no-regrow", action="store_true", help="food does not come back; the episode ends when all is eaten (2026-11-03)")
    ap.add_argument("--clear-bonus", type=int, default=0, help="points per step left when the field is cleared (with --no-regrow)")
    ap.add_argument("--spawn", default="corner", choices=["corner", "random"], help="where enemies appear: the far corners (old) or a random spot away from the worm (2026-11-03)")
    ap.add_argument("--snap-every", type=int, default=0, help="also keep the generation's best every N generations in snaps/ (2026-11-03: gen 1,584 of the heaven worm was lost to best.npz overwrites)")
    ap.add_argument("--seed-from", default=None, help="start from another run's population (state.npz)")
    ap.add_argument("--seed-best", default=None, help="start from one worm: another run's best.npz plus small mutations around it (2026-11-03)")
    ap.add_argument("--free-io", action="store_true", help="evolve the game->sensory and motor->button translator too")
    ap.add_argument("--player", default="worm", choices=["worm", "worm_split", "worm_freefire", "worm_line", "proprio", "plastic", "plastic_evo", "proprio_plastic", "free_proprio_plastic", "free_freefire", "free_line", "fake_freefire", "fake2_freefire", "worm_freefire_v2", "free_freefire_v2"], help="proprio: body feedback; plastic: memory (2026-11-02)")
    a = ap.parse_args()
    global PREDATOR, FREE_IO, KIND, KILL_PTS, ENEMIES, REGROW, CLEAR_BONUS, SPAWN
    SPAWN = a.spawn
    REGROW, CLEAR_BONUS = not a.no_regrow, a.clear_bonus
    PREDATOR, FREE_IO, KILL_PTS, ENEMIES = a.predator, a.free_io, a.kill_pts, a.enemies
    KIND = "free_io" if a.free_io else a.player
    out = f"{RUN}/{a.out}"; os.makedirs(out, exist_ok=True)
    n_param = (sum(FreeIOPlayer.sizes()) if a.free_io or a.player in ("free_freefire", "free_line", "free_freefire_v2") else FreeIOProprioPlasticPlayer.n_params() if a.player == "free_proprio_plastic"
               else PLAYERS[a.player].n_params() if a.player in ("plastic", "plastic_evo", "proprio_plastic")
               else Brain().n_sym_params() if a.sym else Brain.n_params())
    rng = np.random.default_rng(int(time.time()))
    st = f"{out}/state.npz"
    import json
    json.dump({"predator": a.predator, "sym": a.sym or a.free_io or a.player in ("free_proprio_plastic", "free_freefire", "free_line", "free_freefire_v2"), "free_io": a.free_io, "player": "free_io" if a.free_io else a.player, "steps": a.steps, "kill_pts": a.kill_pts, "enemies": a.enemies, "regrow": not a.no_regrow, "clear_bonus": a.clear_bonus, "spawn": a.spawn}, open(f"{out}/meta.json", "w"))   # read by the spectator
    if os.path.exists(st):
        z = np.load(st); popn, gen0, best_ever = z["pop"], int(z["gen"]) + 1, float(z["best"])
    elif a.seed_best:                      # one chosen worm (2026-11-03, user: optimise foraging first, then learn the
        zb = np.load(f"{RUN}/{a.seed_best}/best.npz"); th0 = zb["theta"].astype(np.float32)   # predator: the pink worm)
        popn = th0 + rng.normal(0, a.sigma, (a.pop, th0.size)).astype(np.float32); popn[0] = th0
        gen0, best_ever = int(zb["gen"]) + 1, -1.0
    elif a.seed_from:                      # new world: keep the population, forget the old best score
        z = np.load(f"{RUN}/{a.seed_from}/state.npz"); popn, gen0, best_ever = z["pop"], int(z["gen"]) + 1, -1.0
    else:
        popn, gen0, best_ever = rng.normal(0, 0.3, (a.pop, n_param)).astype(np.float32), 0, -1.0
        popn[0] = 0                                         # the raw connectome itself
        if getattr(PLAYERS[a.player], "N_CONST", 0):        # memory starts switched off (learning rates and constants at
            k = n_param - Brain().n_groups - 3              # their zero point) so evolution turns it on only if it helps
            popn[:, k:] = 0                                 # (D: random rates from gen 0 stayed stuck near 1,300)
    new = not os.path.exists(f"{out}/history.csv")
    hist = open(f"{out}/history.csv", "a", newline=""); w = csv.writer(hist)
    if new:
        w.writerow(["gen", "time", "best", "mean", "median", "best_ever", "secs"])
    with Pool(a.workers) as pool:
        for gen in range(gen0, gen0 + a.gens):
            t = time.time()
            seeds = [int(rng.integers(1 << 30)) for _ in range(a.episodes)]
            fit = np.array(pool.map(evaluate, [(th, seeds, a.steps) for th in popn])); order = np.argsort(-fit)
            if fit[order[0]] > best_ever or gen % 50 == 0:
                # re-test the generation's best on fresh games so one lucky pair of games does not stay "best" forever
                cand = popn[order[0]]
                score = evaluate((cand, [int(rng.integers(1 << 30)) for _ in range(4)], a.steps))
                if score >= best_ever * 0.97 or not os.path.exists(f"{out}/best.npz"):
                    best_ever = max(best_ever, score)
                    np.savez(f"{out}/best.npz", theta=cand, score=score, gen=gen)
                    write_web_json(a.out, out)
            if a.snap_every and gen % a.snap_every == 0:      # the generation's best, kept for later comparisons
                os.makedirs(f"{out}/snaps", exist_ok=True)
                np.savez(f"{out}/snaps/gen_{gen:05d}.npz", theta=popn[order[0]], fit=fit[order[0]], gen=gen)
            w.writerow([gen, time.strftime("%Y-%m-%d %H:%M"), fit[order[0]], round(fit.mean(), 1), np.median(fit), best_ever,
                        round(time.time() - t, 1)]); hist.flush()
            if gen % 10 == 0:
                print(f"[pg] gen {gen:4d} best {fit[order[0]]:5.0f} mean {fit.mean():6.1f} best_ever {best_ever:5.0f} "
                      f"({time.time() - t:.1f}s)", flush=True)
            elite = popn[order[:a.elite]]
            kids = [elite[i % a.elite] + rng.normal(0, a.sigma, n_param).astype(np.float32) for i in range(a.pop - a.elite)]
            popn = np.vstack([elite] + kids)
            np.savez(st, pop=popn, gen=gen, best=best_ever)


if __name__ == "__main__":
    main()
