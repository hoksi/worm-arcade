"""선충 놀이터 (2026-11-01, user: "놀이터를 만들어주자" — a world with food everywhere and no predators, to watch how the
worm moves when nothing hunts it; the worms trained here can then be tried in Super Tank).

A pure-Python copy of the Super Tank playfield, measured from the real game: 236x192 field, the start layout of green
food blocks and red diamonds (playground_layout.npz, captured from MAME), the tank moves 4 px per step and eats what it
drives over (50 points, like the game). No enemies, no shells. When every food is eaten the whole layout comes back
(2026-11-02, user: "먹이는 모두 먹으면 다시 생성되게"; until then each food grew back 300 steps after it was eaten,
which let a worm circle one spot and keep eating). Observations have the exact shape of tankenv.Env, so WormPlayer and a theta trained here run in the game.

predator=True (2026-11-02, user: "선충 놀이터에 포식자 하나 추가"): one red enemy tank, after the game's rules as far as
we know them: it chases the worm (half the worm's speed, sometimes a random turn), fires a shell when the worm is on
its row or column in front of it, and touching it or its shell costs one of 3 lives (잔기). A red diamond gives
ARMOR steps of invincibility (the real game's "super armor"). The worm's own shot (fire) travels along its facing; a
hit sends the enemy back to a corner (no points: the game's kill score is unknown). The game ends with the last life.

enemies=2 (2026-11-03, user: "놀이터에 포식자를 2마리로 늘려서 학습 시켜보자"): as in the real game, a second enemy tank
joins after 300-370 steps (measured: the bottom bar runs out at ~40 % of a game) and stays; both chase, fire and respawn
in the corners farthest from the worm. enemies=1 (default) is the old playground, step for step (same random draws).

  pg = Playground(seed); o = pg.reset(); o, reward, done, died = pg.step(d, fire); png = pg.png(scale=2)
"""
import io, os, random
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 236, 192                      # tankenv.FIELD: playfield inside the yellow border
STEP_PX = 4                          # measured: 4 px per step (4 frames) in every direction
HALF = 6                             # the tank is 13x14 px
FOOD_PTS = 50
ENEMY_PX, SHELL_PX, ARMOR, LIVES = 2, 6, 120, 3
SAFE = 60                            # spawn="random": the least distance (px, city block) from the worm
CORNERS = [(HALF + 2, HALF + 2), (W - HALF - 2, HALF + 2), (HALF + 2, H - HALF - 2), (W - HALF - 2, H - HALF - 2)]
DXY = {0: (0, 0), 1: (0, -1), 3: (1, 0), 5: (0, 1), 7: (-1, 0), 2: (1, -1), 4: (1, 1), 6: (-1, 1), 8: (-1, -1)}


class _Foe:
    """One enemy tank: position, facing, its shell [x, y, dx, dy] and the cooldown before it may fire."""
    def __init__(self):
        self.p, self.face, self.shell, self.cd = None, (0, 1), None, 0


class Playground:
    def __init__(self, seed=0, max_steps=1500, predator=False, kill_pts=0, enemies=1, regrow=True, spawn="corner"):
        # spawn="random" (2026-11-03, user: "놀이터의 포식자는 항상 4면 구석에 출몰했는데 이걸 랜덤으로 수정하는게 좋겠어. 단
        # 선충과 충돌하지 않게" / "학습 놀이터도 개선"): enemies appear and come back at a random spot at least SAFE px
        # (city block) from the worm and not on another enemy. "corner" keeps the old playground, step for step.
        self.spawn = spawn
        # regrow=False (2026-11-03, user: "천국에서 학습 시키고 다 먹으면 종료"): the food does not come back; the episode ends
        # when everything is eaten (self.cleared), so the steps it took measure how good a forager the worm is
        self.regrow = regrow
        self.n_enemies = enemies
        # kill_pts (2026-11-03, user: "적을 맞히면 100점이야"): the real game's score for a hit; 0 keeps the old playground
        self.kill_pts = kill_pts
        z = np.load(f"{HERE}/playground_layout.npz")
        self.walls0 = z["walls"].astype(bool)
        lab, n = ndimage.label(ndimage.binary_dilation(self.walls0, iterations=2))
        self.foods = []                                  # (cx, cy, slice, pixel mask) per green food block
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            m = (lab[sl] == i) & self.walls0[sl]
            self.foods.append(((sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2, sl, m))
        self.diamonds = [tuple(p) for p in z["mines"]]
        self.start = tuple(z["player"])
        self.rng = random.Random(seed)
        self.max_steps = max_steps
        self.predator = predator

    def reset(self, random_start=True):
        self.walls = self.walls0.copy()
        self.gone = set()                                 # eaten food indices ("d<i>" for diamonds)
        self.rounds = 0                                   # times the whole field was eaten clean
        self.cleared = False
        if random_start:
            self.p = [self.rng.uniform(HALF, W - HALF), self.rng.uniform(HALF, H - HALF)]
        else:
            self.p = list(self.start)
        self.t, self.score = 0, 0
        self.lives, self.armor, self.deaths, self.kills = LIVES, 0, 0, 0
        self.face = (0, -1)                                # the tank turns to face the way it moves
        self.my_shell = None                               # [x, y, dx, dy]
        self.foes, self.t2 = [], None
        if self.predator:
            self.foes.append(_Foe()); self._spawn(self.foes[0])
            if self.n_enemies > 1:
                self.t2 = self.rng.randint(300, 370)        # when the second enemy arrives
        return self.observe()

    @property
    def e(self):                                           # the first enemy's position (old single-enemy name)
        return self.foes[0].p if self.foes else None

    def _spawn(self, foe, rank=0):
        if self.spawn == "random":
            for _ in range(200):
                c = [self.rng.uniform(HALF + 2, W - HALF - 2), self.rng.uniform(HALF + 2, H - HALF - 2)]
                if abs(c[0] - self.p[0]) + abs(c[1] - self.p[1]) >= SAFE and \
                        not any(f is not foe and f.p is not None and self._hit(c, f.p, 14) for f in self.foes):
                    foe.p = c; foe.shell, foe.cd = None, 30
                    return
        px, py = self.p                                    # the corner farthest from the worm (rank 1: second farthest)
        foe.p = list(sorted(CORNERS, key=lambda c: -(abs(c[0] - px) + abs(c[1] - py)))[rank])
        foe.shell, foe.cd = None, 30

    def _hit(self, a, b, r=HALF + 1):
        return abs(a[0] - b[0]) <= r and abs(a[1] - b[1]) <= r

    def _lose_life(self):
        self.lives -= 1; self.deaths += 1; self.armor = 60          # a short grace after respawning
        self.p = [self.rng.uniform(HALF, W - HALF), self.rng.uniform(HALF, H - HALF)]
        self.my_shell = None
        for k, f in enumerate(self.foes):
            self._spawn(f, k)

    def _predator_step(self):
        """Enemy moves, both shells fly, hits are checked. Returns True if the worm lost a life."""
        px, py = self.p
        if self.t2 is not None and self.t >= self.t2 and len(self.foes) < self.n_enemies:
            f = _Foe(); self._spawn(f); self.foes.append(f)
        if self.my_shell:                                  # the worm's shot
            s = self.my_shell; s[0] += s[2] * SHELL_PX; s[1] += s[3] * SHELL_PX
            if not (0 <= s[0] < W and 0 <= s[1] < H):
                self.my_shell = None
            else:
                for f in self.foes:
                    if self._hit(s, f.p):
                        self.kills += 1; self.score += self.kill_pts; self.my_shell = None; self._spawn(f)
                        break
        hit = False
        for f in self.foes:
            ex, ey = f.p                                   # chase: close the larger gap, sometimes wander
            if self.rng.random() < 0.2:
                fx, fy = self.rng.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
            elif abs(px - ex) > abs(py - ey):
                fx, fy = (1 if px > ex else -1), 0
            else:
                fx, fy = 0, (1 if py > ey else -1)
            f.face = (fx, fy)
            f.p[0] = min(max(ex + fx * ENEMY_PX, HALF), W - HALF)
            f.p[1] = min(max(ey + fy * ENEMY_PX, HALF), H - HALF)
            f.cd = max(0, f.cd - 1)
            dx, dy = px - f.p[0], py - f.p[1]             # fire when the worm is straight ahead on its line
            if f.shell is None and f.cd == 0:
                for fx, fy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    if (fx and abs(dy) < 6 and dx * fx > 0) or (fy and abs(dx) < 6 and dy * fy > 0):
                        f.face = (fx, fy); f.shell = [f.p[0], f.p[1], fx, fy]; f.cd = 40
                        break
            if f.shell:
                s = f.shell; s[0] += s[2] * SHELL_PX; s[1] += s[3] * SHELL_PX
                if not (0 <= s[0] < W and 0 <= s[1] < H):
                    f.shell = None
            hit = hit or self._hit(self.p, f.p, 2 * HALF) or (f.shell is not None and self._hit(self.p, f.shell))
        if hit and self.armor == 0:
            self._lose_life()
            return True
        return False

    def observe(self):
        mines = [d for i, d in enumerate(self.diamonds) if f"d{i}" not in self.gone]
        enemies = [tuple(f.p) for f in self.foes]
        shells = [tuple(f.shell[:2]) for f in self.foes if f.shell]
        return {"player": (float(self.p[0]), float(self.p[1])), "enemies": enemies, "mines": mines, "shells": shells,
                "walls": self.walls,
                "food_xy": [(f[0], f[1]) for i, f in enumerate(self.foods) if i not in self.gone], "score": self.score, "reserve": max(0, self.lives - 1), "playing": True, "second_enemy": len(self.foes) > 1}

    def step(self, d, fire=False):
        dx, dy = DXY[d]
        if dx or dy:
            self.face = (dx, dy) if not (dx and dy) else (dx, 0)
        if fire and self.predator and self.my_shell is None:
            self.my_shell = [self.p[0], self.p[1], self.face[0], self.face[1]]
        self.p[0] = min(max(self.p[0] + dx * STEP_PX, HALF), W - HALF)
        self.p[1] = min(max(self.p[1] + dy * STEP_PX, HALF), H - HALF)
        self.t += 1
        before = self.score
        px, py = self.p
        for i, (cx, cy, sl, m) in enumerate(self.foods):
            if i not in self.gone and abs(cx - px) <= HALF + 1 and abs(cy - py) <= HALF + 1:
                self.walls[sl] &= ~m; self.gone.add(i); self.score += FOOD_PTS
        for i, (cx, cy) in enumerate(self.diamonds):
            if f"d{i}" not in self.gone and abs(cx - px) <= HALF + 1 and abs(cy - py) <= HALF + 1:
                self.gone.add(f"d{i}"); self.score += FOOD_PTS; self.armor = ARMOR
        if len(self.gone) == len(self.foods) + len(self.diamonds):   # all eaten: the field grows back at once
            if self.regrow:
                self.walls = self.walls0.copy(); self.gone = set(); self.rounds += 1
            else:
                self.cleared = True
        died = False
        if self.predator:
            self.armor = max(0, self.armor - 1)
            died = self._predator_step()
        done = self.t >= self.max_steps or self.lives <= 0 or self.cleared
        return self.observe(), self.score - before, done, died

    def frame(self, heading=0):
        """RGB image in the game's look: yellow border, green food, red diamonds, yellow tank with its barrel."""
        img = np.zeros((H + 8, W + 8, 3), np.uint8)
        img[:2], img[-2:], img[:, :2], img[:, -2:] = (230, 230, 0), (230, 230, 0), (230, 230, 0), (230, 230, 0)
        f = img[4:-4, 4:-4]
        f[self.walls] = (0, 200, 0)
        for i, (cx, cy) in enumerate(self.diamonds):
            if f"d{i}" not in self.gone:
                x, y = int(cx), int(cy)
                for k in range(-2, 3):
                    f[max(0, y - 2 + abs(k)):y + 3 - abs(k), max(0, x + k):x + k + 1] = (230, 0, 0)
        for foe in (self.foes if self.predator else []):
            ex, ey = int(foe.p[0]), int(foe.p[1])
            f[max(0, ey - HALF):ey + HALF + 1, max(0, ex - HALF):ex + HALF + 1] = (230, 0, 0)
            f[max(0, ey - 3):ey + 4, max(0, ex - 3):ex + 4] = (120, 0, 0)
            for k in range(HALF + 4):
                xx, yy = ex + foe.face[0] * k, ey + foe.face[1] * k
                if 0 <= xx < W and 0 <= yy < H:
                    f[max(0, yy - 1):yy + 2, max(0, xx - 1):xx + 2] = (230, 0, 0)
        if self.predator:
            for s, c in [(foe.shell, (255, 80, 80)) for foe in self.foes] + [(self.my_shell, (255, 255, 120))]:
                if s and 0 <= s[0] < W and 0 <= s[1] < H:
                    sx, sy = int(s[0]), int(s[1]); f[max(0, sy - 1):sy + 2, max(0, sx - 1):sx + 2] = c
        x, y = int(self.p[0]), int(self.p[1])
        body = (255, 255, 255) if self.armor and self.t % 4 < 2 else (230, 230, 0)     # armour blinks
        f[max(0, y - HALF):y + HALF + 1, max(0, x - HALF):x + HALF + 1] = body
        f[max(0, y - 3):y + 4, max(0, x - 3):x + 4] = (120, 120, 0)
        hx, hy = [(0, -1), (1, 0), (0, 1), (-1, 0)][heading]
        for k in range(HALF + 4):
            xx, yy = x + hx * k, y + hy * k
            if 0 <= xx < W and 0 <= yy < H:
                f[max(0, yy - (hx != 0)):yy + 1 + (hx != 0), max(0, xx - (hy != 0)):xx + 1 + (hy != 0)] = (230, 230, 0)
        return img

    def png(self, heading=0, scale=2):
        from PIL import Image
        im = Image.fromarray(self.frame(heading))
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
        return buf.getvalue()


if __name__ == "__main__":                              # quick look: python playground.py out.png
    import sys, time
    from worm import WormPlayer
    pg = Playground(1); o = pg.reset(); pl = WormPlayer(None, None); t = time.time()
    for _ in range(300):
        o, r, done, _ = pg.step(*pl.act(o))
    print("300 steps", round(time.time() - t, 2), "s, score", pg.score)
    open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/pg.png", "wb").write(pg.png(pl.heading))
