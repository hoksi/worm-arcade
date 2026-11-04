"""선충, 슈퍼탱크 세계에 환생하다 (2026-10-31). C. elegans connectome as a Super Tank player.

Connectome: OpenWorm c302 data/herm_full_edgelist.csv (Cook et al. 2019, hermaphrodite; neurons + muscles; MIT-licensed
repo). GABAergic neurons (McIntire et al. 1993: DD, VD, RME, AVL, DVB, RIS) make inhibitory chemical synapses, every
other chemical synapse excites; gap junctions couple both ways.

The game is the worm's world (user, 2026-10-31):
  green blocks + red diamonds = food  -> smell change while the head sweeps: rising -> ASEL/AWA, falling -> ASER/AWC
  enemy tanks = predators             -> head nociceptors ASH/ADL in front, tail phasmids PHA/PHB behind
  enemy shells = predator attacks     -> touch ALM/AVM (front) or PLM/PVM (behind) + the blocked side's body touch,
                                         so the worm side-steps toward the free side (user: dodge left or right)
  the yellow border                   -> nose touch FLP/OLQ ahead, body touch ALM/PLM/PVD along the sides (v5: green blocks
                                         are food the tank crawls over, not walls)
  food right in front                 -> pharyngeal pacemaker MC -> pumping (eating; v5: no longer fires, blocks are
                                         eaten by crawling over them); no satiety
  predator in a clear line            -> pharyngeal I2 (noxious) -> spitting = fire, and only then (v5)
Readout: forward (AVB, VB, DB) - backward (AVA, VA, DA) moves along the heading; left vs right head motor neurons
(SMD, RMD) turn the heading 90 degrees and step; pharyngeal activity fires.
"""
import csv, os, random
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
GABA = {f"DD0{i}" for i in range(1, 7)} | {f"VD{i:02d}" for i in range(1, 14)} | {"RMED", "RMEL", "RMER", "RMEV", "AVL", "DVB", "RIS"}
HEADINGS = [(0, -1), (1, 0), (0, 1), (-1, 0)]          # up, right, down, left (rotated screen)
DIR_INDEX = {(0, -1): 1, (1, 0): 3, (0, 1): 5, (-1, 0): 7}


def load(shuffle_seed=None):
    """-> names, chemical matrix C[target, source] (signed counts), gap matrix G (symmetric counts).
    shuffle_seed: degree-preserving rewiring of both networks (the 'fake worm' control)."""
    rows = [[c.strip() for c in r] for r in csv.reader(open(f"{HERE}/data/herm_full_edgelist.csv"))][1:]
    names = sorted({r[0] for r in rows} | {r[1] for r in rows})
    idx = {n: i for i, n in enumerate(names)}
    chem = [(idx[s], idx[t], float(w)) for s, t, w, k in rows if k == "chemical"]
    gap = [(idx[s], idx[t], float(w)) for s, t, w, k in rows if k == "electrical"]
    if shuffle_seed is not None:
        rnd = random.Random(shuffle_seed)
        chem = _rewire(chem, rnd)
        gap = _rewire(gap, rnd)
    n = len(names)
    C, G = np.zeros((n, n), np.float32), np.zeros((n, n), np.float32)
    for s, t, w in chem:
        C[t, s] += -w if names[s] in GABA else w
    for s, t, w in gap:
        G[t, s] += w; G[s, t] += w
    G /= 2                                                   # the list holds both directions
    return names, C, G


def _rewire(edges, rnd, swaps=10):
    """Swap targets of random edge pairs (keeps every node's in- and out-degree)."""
    e = [list(x) for x in edges]
    for _ in range(swaps * len(e)):
        a, b = rnd.randrange(len(e)), rnd.randrange(len(e))
        if e[a][0] != e[b][1] and e[b][0] != e[a][1]:
            e[a][1], e[b][1] = e[b][1], e[a][1]
    return [tuple(x) for x in e]


class Brain:
    """Graded neurons with a firing threshold:
        v += 0.3 * (-v + relu(tanh(K * (C (out * a) + gap) + bias + I - TH)))
    out[j] scales what neuron j sends (its sign included): evolution may turn a neuron inhibitory, the way a real neuron
    uses one transmitter for all its outputs. Defaults (out = 1, bias = 0) = the raw connectome (stage 1).
    Stage-1 sweep (2026-10-31): K=5, TH=0.2 keeps the brain quiet without input; nose touch -> reversal and food in the
    mouth -> pumping come out of the wiring alone. Larger K or lower TH lights up ~90 % of the brain for any stimulus."""
    # v3 (2026-10-31, after the saturated run): K=4 with adaptation 1.5 keeps ~1/4 of the brain active and the motor
    # readout follows the input (resp_probe.py); without adaptation ~90 % stays lit and outputs never change.
    K, TH, ADAPT = 4.0, 0.2, 1.5

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        self.names, C, G = load(shuffle_seed)
        self.idx = {n: i for i, n in enumerate(self.names)}
        n = self.n = len(self.names)
        cin = np.abs(C).sum(1, keepdims=True) + G.sum(1, keepdims=True) + 1
        self.C, self.G = C / cin, G / cin                    # keep each node's total input in range
        self.Gdeg = self.G.sum(1)
        self.out, self.bias = np.ones(n, np.float32), np.zeros(n, np.float32)
        self.readout = np.array([0.02, 0.005, 0.3], np.float32)  # thresholds: move, turn (dorsal-ventral is subtle), fire
        # bilateral pairs (AWCL/AWCR, SMDDL/SMDDR, ...) share one group: a theta of length 2*groups+3 is the left-right
        # symmetric form (2026-11-02, user chose "1번 적용": the pair are the same cell type, but free evolution had made
        # AIYL excitatory and AIYR inhibitory); 2*n+3 stays the per-neuron form of the earlier runs
        gid = {}
        for nm in self.names:
            key = nm[:-1] + "*" if nm[-1] in "LR" and (nm[:-1] + ("R" if nm[-1] == "L" else "L")) in self.idx else nm
            gid.setdefault(key, len(gid))
        self.group = np.array([gid[nm[:-1] + "*" if nm[-1] in "LR" and (nm[:-1] + ("R" if nm[-1] == "L" else "L")) in self.idx else nm]
                               for nm in self.names])
        self.n_groups = len(gid)
        if params is not None:
            self.set_params(params)
        self.substeps, self.v, self.u = substeps, np.zeros(n, np.float32), np.zeros(n, np.float32)
        g = lambda pat: [self.idx[x] for x in self.names if _match(x, pat)]
        self.S = {k: g(p) for k, p in SENSORY.items()}
        self.M = {k: g(p) for k, p in MOTOR.items()}

    @staticmethod
    def n_params(n=448):
        return 2 * n + 3

    def n_sym_params(self):
        return 2 * self.n_groups + 3

    def set_params(self, p):
        n = self.n
        if len(p) == self.n_sym_params():                  # left-right symmetric theta: expand groups to neurons
            g = self.n_groups
            p = np.concatenate([p[:g][self.group], p[g:2 * g][self.group], p[2 * g:]])
        self.out = np.clip(1 + p[:n], -2, 2).astype(np.float32)
        self.bias = np.clip(0.5 * p[n:2 * n], -0.5, 0.5).astype(np.float32)
        lo, hi = np.array([0.005, 0.001, 0.1]), np.array([0.1, 0.03, 0.6])
        self.readout = (lo + (hi - lo) * (1 + np.tanh(p[2 * n:2 * n + 3])) / 2).astype(np.float32)
        self._W = None

    def reset(self):
        self.v[:] = 0; self.u[:] = 0

    def step(self, inputs):
        if isinstance(inputs, np.ndarray):                 # a ready input-current vector (FreeIOPlayer)
            I = inputs.astype(np.float32)
        else:
            I = np.zeros_like(self.v)
            for k, val in inputs.items():
                I[self.S[k]] += val
        if getattr(self, "_W", None) is None:
            # one sparse matrix for C*out + G - diag(Gdeg): same drive, ~3x faster (2026-11-01, for the playground runs)
            from scipy import sparse
            self._W = sparse.csr_matrix(self.C * self.out[None, :] + self.G - np.diag(self.Gdeg)).astype(np.float32)
        for _ in range(self.substeps):
            a = self.v
            drive = self._W @ a
            self.v = a + 0.3 * (-a + np.maximum(0, np.tanh(self.K * drive + self.bias + I - self.TH - self.ADAPT * self.u)))
            self.u += 0.05 * (self.v - self.u)        # adaptation: a neuron that stays on tires and lets go
        return {k: float(self.v[i].mean()) for k, i in self.M.items()}


def _match(name, pats):
    return any(name == p or (p.endswith("*") and name.startswith(p[:-1])) for p in pats)


SENSORY = {
    # v2 (2026-10-31, user questions: too much food saturates smell; is smell only left/right; shells from behind; walls)
    "smell_up": ["ASEL", "AWAL", "AWAR"],            # odour rising: ASEL is an ON cell, AWA attraction -> keep going
    "smell_down": ["ASER", "AWCL", "AWCR"],          # odour falling: ASER OFF cell, AWC fires on odour removal -> turn
    # v6 (2026-11-01, user watching: the worm sensed predators but not where): four directions relative to its facing
    "pred_front": ["ASHL", "ASHR"],                  # head nociceptors: danger ahead
    "pred_back": ["PHAL", "PHAR", "PHBL", "PHBR"],   # tail phasmids: danger behind
    "pred_L": ["ADLL", "ASKL"], "pred_R": ["ADLR", "ASKR"],   # the other avoidance pairs carry the side (dorsal / ventral)
    "touch_front": ["ALML", "ALMR", "AVM"], "touch_back": ["PLML", "PLMR", "PVM"],
    # body sides map to dorsal/ventral too: ALM/PLM sit laterally, so the side cue goes to the dorsal (ALM) vs ventral
    # (AVM/PVM) touch cells and to the PVD L/R pair
    "touch_L": ["ALML", "ALMR", "PVDL"], "touch_R": ["AVM", "PVM", "PVDR"],
    "nose": ["FLPL", "FLPR", "OLQDL", "OLQDR", "OLQVL", "OLQVR"],
    "mouth_food": ["MCL", "MCR"], "mouth_noxious": ["I2L", "I2R"],
}
MOTOR = {
    "fwd": ["AVBL", "AVBR", "VB*", "DB*"], "back": ["AVAL", "AVAR", "VA*", "DA*"],
    # a worm crawls on its side, so its turns are dorsal/ventral head bends, not left/right (L/R neurons are mirror
    # images and stayed equal: the first worms never turned, 2026-10-31). Game "left" = dorsal, "right" = ventral.
    "left": ["SMDDL", "SMDDR", "RMDDL", "RMDDR", "RMED"], "right": ["SMDVL", "SMDVR", "RMDVL", "RMDVR", "RMEV"],
    "pump": ["pm4*", "pm5*", "MCL", "MCR"], "spit": ["M1", "pm3*"],
}


class WormPlayer:
    """Turns a tankenv observation into the worm's senses, and its motor state into a (direction, fire) action."""

    name = "worm"
    NOXIOUS_OLD = True          # 2026-11-03: False = "predator ahead" for the mouth is the whole line ahead (no green-block / 150 px limits)
    FIRE_GATE = True            # 2026-11-03: False = no "fire only at a predator ahead" rule (WormFreeFirePlayer)
    PRED_SPLIT = False          # 2026-11-03: True = a diagonal predator is felt on both sides (WormSplitPlayer)
    SHELL_OLD = True            # 2026-11-03: False = an enemy shell is felt anywhere on the worm's row/column (user: "적 포탄이 앞 / 뒤는
                                # 그줄 전체로 하는게 맞을것 같아"), not only within 80 px, on the side it comes from (front/back/left/
                                # right), without the blocked-side hint. Default kept so running/queued runs are unchanged.

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        self.brain = Brain(shuffle_seed, params, substeps)
        self.heading, self.prev, self.turn_cd = 0, None, 0
        self.log = []

    def senses(self, o):
        """Head-swing klinotaxis: the head point sweeps left/right on alternate steps and the smell there (nearest few
        foods only, so a field full of food does not saturate) is compared with the last sample; rising -> smell_up,
        falling -> smell_down. Real worms find food from these changes, not from a left/right difference."""
        p = o["player"]
        if p is None:
            return {}
        hx, hy = HEADINGS[self.heading]
        lx, ly = hy, -hx                                             # the worm's left (screen y grows downwards)
        px, py = p
        s = {k: 0.0 for k in SENSORY}
        self.sweep = -getattr(self, "sweep", 1)
        head = (px + hx * 6 + lx * 3 * self.sweep, py + hy * 6 + ly * 3 * self.sweep)
        # the playground (playground.py) knows its food positions; the game has to find the blocks in the picture
        foods = (o["food_xy"] if "food_xy" in o else _blocks(o["walls"])) + [(x, y) for x, y in o["mines"]]
        near = sorted(foods, key=lambda f: abs(f[0] - head[0]) + abs(f[1] - head[1]))[:3]
        smell = sum(np.exp(-(abs(fx - head[0]) + abs(fy - head[1])) / 40) for fx, fy in near)
        ds = smell - getattr(self, "last_smell", smell)
        self.last_smell = smell
        s["smell_up" if ds > 0 else "smell_down"] = min(abs(ds) / (smell + 0.05) * 3, 1.0)   # relative change
        for fx, fy in foods:                                           # food right in front: eat it
            dx, dy = fx - px, fy - py
            if abs(dx * lx + dy * ly) < 6 and 0 < dx * hx + dy * hy < 24:
                s["mouth_food"] = 1.0
                break
        for ex, ey in o["enemies"]:
            dx, dy = ex - px, ey - py
            d = abs(dx) + abs(dy) + 1
            fwd, side = dx * hx + dy * hy, dx * lx + dy * ly
            if self.PRED_SPLIT:                # split by the share of each axis: a diagonal enemy is felt ahead and aside
                tot = abs(fwd) + abs(side) + 1e-6
                s["pred_front" if fwd > 0 else "pred_back"] += 3 * np.exp(-d / 50) * abs(fwd) / tot
                s["pred_L" if side > 0 else "pred_R"] += 3 * np.exp(-d / 50) * abs(side) / tot
            elif abs(fwd) >= abs(side):
                s["pred_front" if fwd > 0 else "pred_back"] += 3 * np.exp(-d / 50)
            else:
                s["pred_L" if side > 0 else "pred_R"] += 3 * np.exp(-d / 50)
            # spit (= fire) only at a predator straight ahead along the barrel, with nothing in between (v6: before,
            # any predator on the same row or column counted, behind or beside too)
            if fwd > 0 and abs(side) < 6 and (not self.NOXIOUS_OLD or (d < 150 and _clear(o["walls"], p, (ex, ey)))):
                s["mouth_noxious"] = 1.0
        # v5: green blocks are food the tank drives over (eat_test.py: driving alone cleared 22 % and scored 1,150), so touch
        # only reacts to the yellow border; before, a block ahead pressed the nose and the worm backed away from its food
        free_l, free_r = _inside(p, (lx, ly), 10), _inside(p, (-lx, -ly), 10)
        for sx, sy in o.get("shells", []):
            dx, dy = sx - px, sy - py
            if not self.SHELL_OLD:
                # 2026-11-03 (user: "좌/우에서 날아오는 포탄은 어떻게 감지할 수 있을까?" -> "진행"): a shell anywhere on the
                # worm's line is felt on the body part it would hit: ahead/behind -> head/tail touch, from the left/right ->
                # the dorsal/ventral body touch on that side (the worm lies on its side). No "blocked side" hint: which way
                # to dodge is left to evolution. Before, a shell from the side was felt as "behind".
                fwd, side = dx * hx + dy * hy, dx * lx + dy * ly
                if abs(side) < 8:
                    s["touch_front" if fwd > 0 else "touch_back"] += 1.0
                elif abs(fwd) < 8:
                    s["touch_L" if side > 0 else "touch_R"] += 1.0
                continue
            if (abs(dx) < 8 or abs(dy) < 8) and abs(dx) + abs(dy) < 80:
                s["touch_front" if dx * hx + dy * hy > 0 else "touch_back"] += 0.5
                # front or back alike: side-step (user: a shell from behind needs a left/right turn too); touch the
                # side that is blocked so the worm turns toward the free side
                s["touch_L" if free_r >= free_l else "touch_R"] += 1.5
        if not free_l:
            s["touch_L"] += 0.7                                       # a wall along the body
        if not free_r:
            s["touch_R"] += 0.7
        if not _inside(p, (hx, hy), 12):
            s["nose"] = 1.0
        for k in ("pred_front", "pred_back", "pred_L", "pred_R"):
            s[k] = min(s[k], 2.0)
        return s

    def act(self, o):
        p = o["player"]
        if p is None:                                                   # exploding / respawning
            self.brain.reset(); self.heading = 0
            return 0, False
        s = self.senses(o)
        m = self.brain.step(s)
        th_move, th_turn, th_fire = self.brain.readout
        move, turn = m["fwd"] - m["back"], m["left"] - m["right"]
        # v5 (2026-11-01, user: shooting food wastes the shot; fire only when a predator is straight ahead). Blocks are eaten
        # by crawling over them, so pumping (eating) no longer fires; only spitting at a predator in a clear line does.
        fire = m["spit"] > th_fire and (not self.FIRE_GATE or s.get("mouth_noxious", 0) > 0)
        self.log.append((s, m))
        if self.turn_cd > 0:
            self.turn_cd -= 1
        elif abs(turn) > th_turn:
            self.heading = (self.heading + (-1 if turn > 0 else 1)) % 4    # left turn = counter-clockwise
            self.turn_cd = 3
            return DIR_INDEX[HEADINGS[self.heading]], fire                  # turn and step: a side-step
        if move > th_move:
            return DIR_INDEX[HEADINGS[self.heading]], fire
        if move < -th_move:
            # the tank turns to face every way it moves, so backing up = turning round (v6: the worm's idea of
            # "front" used to stay put while the barrel pointed the other way)
            self.heading = (self.heading + 2) % 4
            return DIR_INDEX[HEADINGS[self.heading]], fire
        return 0, fire


def _blocks(walls):
    lab, n = ndimage.label(ndimage.binary_dilation(walls, iterations=2))
    return [((sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2) for sl in ndimage.find_objects(lab)]


def _clear(walls, p, e):
    x0, y0, x1, y1 = int(p[0]), int(p[1]), int(e[0]), int(e[1])
    if abs(x1 - x0) < 6:
        lo, hi = sorted((y0, y1)); return not walls[lo:hi, max(0, x0 - 2):x0 + 3].any()
    lo, hi = sorted((x0, x1)); return not walls[max(0, y0 - 2):y0 + 3, lo:hi].any()


FIELD_W, FIELD_H = 236, 192                      # playfield inside the yellow border (tankenv.FIELD)


def _inside(p, d, dist):
    x, y = p[0] + d[0] * dist, p[1] + d[1] * dist
    return int(4 <= x < FIELD_W - 4 and 4 <= y < FIELD_H - 4)


def _free(walls, p, d, dist=16):
    x, y = int(p[0] + d[0] * dist), int(p[1] + d[1] * dist)
    if not (0 <= x < walls.shape[1] and 0 <= y < walls.shape[0]):
        return 0
    return int(not walls[max(0, y - 4):y + 5, max(0, x - 4):x + 5].any())


# ---- free input/output (2026-11-02, user: "입력에 대한 출력을 우리가 해석해서 동작시키는거잖아" -> compare with a worm whose
# translator is evolved too). The 13 game senses are not wired to chosen neurons: an evolved 13 x groups matrix spreads
# them over the worm's sensory neurons (left-right pairs share a weight). The 5 actions (fwd, back, left, right, spit)
# are read as evolved weightings of the same 65 motor-pool nodes the hand-made readout uses. Theta =
# [symmetric brain params | input matrix | output matrix]; the readout thresholds and the fire gate stay as in WormPlayer.
FREE_IN_CANDS = ['ADF', 'ADL', 'AFD', 'ASE', 'ASG', 'ASH', 'ASI', 'ASJ', 'ASK', 'AWA', 'AWB', 'AWC', 'PHA', 'PHB', 'PHC', 'ALM',
                 'AVM', 'PLM', 'PVM', 'PVD', 'FLP', 'OLQD', 'OLQV', 'CEPD', 'CEPV', 'IL1D', 'IL1V', 'IL1', 'IL2D', 'IL2V', 'IL2',
                 'URX', 'URY', 'URAD', 'URAV', 'BAG', 'AQR', 'PQR', 'ADE', 'PDE', 'I1', 'I2', 'MC', 'NSM']
SENSE_KEYS = list(SENSORY)
ACTIONS = ["fwd", "back", "left", "right", "spit"]


class FreeIOPlayer(WormPlayer):
    name = "worm-free-io"
    sense_keys = SENSE_KEYS

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        super().__init__(shuffle_seed, None, substeps)
        b = self.brain
        ins = [i for i, nm in enumerate(b.names) if any(nm == c or (nm.startswith(c) and nm[len(c):] in ("L", "R", "DL", "DR", "VL", "VR"))
                                                          for c in FREE_IN_CANDS)]
        key = lambda nm: nm[:-1] if nm[-1] in "LR" and (nm[:-1] + ("R" if nm[-1] == "L" else "L")) in b.idx else nm
        groups = sorted({key(b.names[i]) for i in ins})
        self.in_idx = np.array(ins); self.in_group = np.array([groups.index(key(b.names[i])) for i in ins])
        self.in_groups = groups
        self.out_idx = np.array(sorted({i for v in b.M.values() for i in v}))
        if params is not None:
            self.set_theta(params)

    @classmethod
    def sizes(cls):
        p = cls()
        return p.brain.n_sym_params(), len(cls.sense_keys) * len(p.in_groups), len(ACTIONS) * len(p.out_idx)

    def set_theta(self, theta):
        nb, ni, no = self.brain.n_sym_params(), len(self.sense_keys) * len(self.in_groups), len(ACTIONS) * len(self.out_idx)
        self.brain.set_params(theta[:nb])
        self.Win = theta[nb:nb + ni].reshape(len(self.sense_keys), len(self.in_groups))
        self.Wout = theta[nb + ni:nb + ni + no].reshape(len(ACTIONS), len(self.out_idx))

    def act(self, o):
        p = o["player"]
        if p is None:
            self.brain.reset(); self.heading = 0
            return 0, False
        s = self.senses(o)
        x = np.array([s.get(k, 0.0) for k in self.sense_keys], np.float32)
        I = np.zeros(self.brain.n, np.float32)
        I[self.in_idx] = (x @ self.Win)[self.in_group]
        self.brain.step(I)
        y = self.Wout @ self.brain.v[self.out_idx] / len(self.out_idx) * 10
        m = dict(zip(ACTIONS, map(float, y)))
        th_move, th_turn, th_fire = self.brain.readout
        move, turn = m["fwd"] - m["back"], m["left"] - m["right"]
        fire = m["spit"] > th_fire and (not self.FIRE_GATE or s.get("mouth_noxious", 0) > 0)
        self.log.append((s, m))
        if self.turn_cd > 0:
            self.turn_cd -= 1
        elif abs(turn) > th_turn:
            self.heading = (self.heading + (-1 if turn > 0 else 1)) % 4
            self.turn_cd = 3
            return DIR_INDEX[HEADINGS[self.heading]], fire
        if move > th_move:
            return DIR_INDEX[HEADINGS[self.heading]], fire
        if move < -th_move:
            self.heading = (self.heading + 2) % 4
            return DIR_INDEX[HEADINGS[self.heading]], fire
        return 0, fire


# ---- body feedback (2026-11-02, user: "자기 움직임을 되돌려 받는 감각도 시뮬레이션 가능할까?" -> "기억과 감각 되돌려주기가
#더 흥미 있을것 같아"). The worm is told what its body actually did on the last step, through cells known to sense
# the body: DVA (stretch receptor) and the B-type motor neurons VB/DB (proprioceptive: they sense the bend ahead of
# them) when it really moved forward, DVA alone when it moved backward; SMD and SAA (head neurons with stretch-
# sensitive processes) on the side the head bent. How the brain uses it is left to evolution (the SMD -> RIA
# corollary-discharge wiring is already in the connectome). No behaviour rule is added.
PROPRIO = {
    "prop_fwd": ["DVA", "VB*", "DB*"], "prop_back": ["DVA"],
    "prop_dorsal": ["SMDDL", "SMDDR", "SAADL", "SAADR"], "prop_ventral": ["SMDVL", "SMDVR", "SAAVL", "SAAVR"],
}


class ProprioPlayer(WormPlayer):
    name = "worm-proprio"

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        super().__init__(shuffle_seed, params, substeps)
        b = self.brain
        b.S.update({k: [b.idx[x] for x in b.names if _match(x, p)] for k, p in PROPRIO.items()})
        self._pos, self._turn = None, 0

    def senses(self, o):
        s = super().senses(o)
        p = o["player"]
        if p is not None and self._pos is not None:
            hx, hy = HEADINGS[self.heading]
            along = (p[0] - self._pos[0]) * hx + (p[1] - self._pos[1]) * hy
            if along > 1:
                s["prop_fwd"] = 0.5
            elif along < -1:
                s["prop_back"] = 0.5
            if self._turn == 3:
                s["prop_dorsal"] = 0.5                     # heading - 1 = a "left" (dorsal) turn in act()
            elif self._turn == 1:
                s["prop_ventral"] = 0.5
        self._pos = p
        return s

    def act(self, o):
        h0 = self.heading
        a = super().act(o)
        self._turn = (self.heading - h0) % 4
        return a


# ---- memory: reward-modulated plasticity (2026-11-02, same request). Three-factor rule on the existing synapses only:
# every synapse keeps an eligibility trace of "pre and post were on together"; eating (+1, like NSM's serotonin food
# signal) or being caught (-1) turns the recent traces into lasting changes. Evolution sets each neuron group's learning
# rate (left-right pairs share; negative = anti-Hebbian); the trace decay and forgetting are fixed. Theta =
# [symmetric brain params | learning rate per group]. Changes live for one game (one life history), then reset.
ELIG_DECAY, FORGET, P_MAX, ETA_SCALE = 0.9, 0.002, 0.5, 0.05


class PlasticPlayer(WormPlayer):
    name = "worm-plastic"
    # 2026-11-02 (user: "c+d 와 b+c+d 에 전략에 반영"): D showed memory is used (off: 1,229 -> 496) but the trace decay,
    # forgetting rate and change cap were hand-set. Subclasses with N_CONST = 3 let evolution set them too; a zero param
    # gives the old value (0.9, 0.002, 0.5), so D's layout and results are unchanged (N_CONST = 0).
    N_CONST = 0

    @staticmethod
    def consts(q):
        q = np.zeros(3, np.float32) if q is None or len(q) == 0 else np.asarray(q, np.float32)
        decay = float(np.clip(1 - (1 - ELIG_DECAY) * np.exp(q[0]), 0.3, 0.995))
        forget = float(np.clip(FORGET * np.exp(q[1]), 1e-5, 0.05))
        pmax = float(np.clip(P_MAX * np.exp(q[2]), 0.02, 2.0))
        return decay, forget, pmax

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        super().__init__(shuffle_seed, None, substeps)
        b = self.brain
        nb = b.n_sym_params()
        if params is not None:
            b.set_params(params[:nb])
            self._init_plastic(params[nb:nb + b.n_groups], params[nb + b.n_groups:nb + b.n_groups + self.N_CONST])
        else:
            self._init_plastic(None)

    def _init_plastic(self, eta_params, const_params=None):
        b = self.brain
        self.eta_group = (ETA_SCALE * np.tanh(np.asarray(eta_params, np.float32)) if eta_params is not None
                          else np.zeros(b.n_groups, np.float32))
        b._W = None; b.step(np.zeros(b.n, np.float32)); b.reset()      # (re)builds b._W
        W = b._W
        self.rows = np.repeat(np.arange(b.n), np.diff(W.indptr)); self.cols = W.indices
        self.W0 = W.data.copy(); self.P = np.zeros_like(self.W0); self.E = np.zeros_like(self.W0)
        self.eta = self.eta_group[b.group][self.rows]
        self._score, self._reserve, self.reward_total = None, None, 0.0
        self.decay, self.forget, self.pmax = self.consts(const_params if self.N_CONST else None)

    @classmethod
    def n_params(cls):
        b = Brain()
        return b.n_sym_params() + b.n_groups + cls.N_CONST

    def act(self, o):
        r = 0.0
        if self._score is not None:
            r += (o.get("score", 0) - self._score) / 50.0   # one food = +1
            if o.get("reserve", 0) < self._reserve:
                r -= 1.0                                    # caught
        self._score, self._reserve = o.get("score", 0), o.get("reserve", 0)
        if r:
            self.P += self.eta * r * self.E
            np.clip(self.P, -self.pmax, self.pmax, out=self.P)
            self.reward_total += r
        self.P *= 1 - self.forget
        self.brain._W.data = self.W0 + self.P
        a = super().act(o)
        v = self.brain.v
        self.E = self.decay * self.E + v[self.rows] * v[self.cols]
        return a


class PlasticEvoPlayer(PlasticPlayer):
    """E (2026-11-02, user: "D는 E로 하여 다시 측정"): D with the C+D / B+C+D memory setup, so memory-only can be compared
    fairly: decay, forgetting and cap evolved (N_CONST = 3), memory switched off at gen 0."""
    name = "worm-plastic-evo"
    N_CONST = 3


class ProprioPlasticPlayer(PlasticPlayer, ProprioPlayer):
    """C+D (2026-11-02, user: "C+D 도 추가 하는게 나을까?"): body feedback and memory together."""
    name = "worm-proprio-plastic"
    N_CONST = 3



class FreeIOProprioPlasticPlayer(PlasticPlayer, ProprioPlayer, FreeIOPlayer):
    """B+C+D (2026-11-02, user: "B+C+D 는 어떤 결과가 나올지 궁금함" / body feedback handed to the translator too:
    "맡긴다에 동의함"): evolved translator for the 13 game senses and the 4 body-feedback signals, body feedback, and
    memory. Theta = [symmetric brain | input matrix (17 x groups) | output matrix | learning rate per group]."""
    name = "worm-free-proprio-plastic"
    sense_keys = SENSE_KEYS + list(PROPRIO)
    N_CONST = 3

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        PlasticPlayer.__init__(self, shuffle_seed, None, substeps)
        if params is not None:
            nb, ni, no = self.brain.n_sym_params(), len(self.sense_keys) * len(self.in_groups), len(ACTIONS) * len(self.out_idx)
            self.set_theta(params[:nb + ni + no])
            k = nb + ni + no + self.brain.n_groups
            self._init_plastic(params[nb + ni + no:k], params[k:k + self.N_CONST])

    @classmethod
    def n_params(cls):
        nb, ni, no = cls.sizes()
        return nb + ni + no + Brain().n_groups + cls.N_CONST


class WormSplitPlayer(WormPlayer):
    """A with the predator sense split over two directions (2026-11-03, user: "두방향으로 나눠 넣는게 가장 자연스러울것
    같아"): an enemy ahead-right drives the 'ahead' and 'right' neurons in proportion to how far ahead and how far right
    it is, as a real worm feels a smell on several parts of its body at once. The total strength is unchanged."""
    name = "worm-split"
    PRED_SPLIT = True


class WormFreeFirePlayer(WormPlayer):
    """A without the firing rule (2026-11-03, user: "정면의 적에게 뱉기를 디지털 선충이 진화과정에서 발현하게 하려면"):
    spitting fires whenever the spit motor neurons pass the evolved threshold. The pharyngeal I2 still feels a predator
    straight ahead (mouth_noxious), but whether that feeling reaches spitting is left to the evolved brain. Natural cost:
    one shell at a time, so a wasted shot leaves the worm unarmed. Trained with kill_pts=100 (the real game's hit score)."""
    name = "worm-freefire"
    FIRE_GATE = False
    # user 2026-11-03: "게임에서 적과 나 사이에 벽은 없는데" / "포탄은 발사하면 화면 끝까지 날아가고 발사한 포탄이 사라지기전까지
    # 포탄을 다시 발사 할 수 없어": the green blocks (o["walls"]) are mines, not walls, and the shell flies to the screen
    # edge, so the mouth feels any predator on the line ahead
    NOXIOUS_OLD = False


class WormLinePlayer(WormPlayer):
    """Control for WormFreeFirePlayer: the same whole-line 'predator ahead' sense, the firing rule kept."""
    name = "worm-line"
    NOXIOUS_OLD = False


class FreeIOFreeFirePlayer(FreeIOPlayer):
    """B without the firing rule (2026-11-03, user: "B는 어떻게 접근해야 할까?" -> "3개 실험 진행"): the evolved input
    matrix decides where 'predator straight ahead' goes and the evolved output matrix decides which motor neurons spit, so
    any aiming has to be found from scratch. Whole-line mouth sense, trained with the real game's 200 points per kill."""
    name = "worm-free-io-freefire"
    FIRE_GATE = False
    NOXIOUS_OLD = False


class WormFreeFireV2Player(WormFreeFirePlayer):
    """A without the firing rule, with the shell sense the user chose on 2026-11-03 (SHELL_OLD=False: a shell anywhere on
    the worm's line, felt on the side it comes from, no dodge hint). First trained with two enemies."""
    name = "worm-freefire-v2"
    SHELL_OLD = False


class FreeIOLinePlayer(FreeIOPlayer):
    """Control for FreeIOFreeFirePlayer: same whole-line sense, firing rule kept."""
    name = "worm-free-io-line"
    NOXIOUS_OLD = False


class WormFakeFreeFirePlayer(WormFreeFirePlayer):
    """'Fake worm' control for WormFreeFirePlayer (2026-11-03, user: "가짜 뇌 실험을 준비해줘"): the same 448 neurons, the
    same input and readout neurons, every neuron keeping its number of incoming and outgoing connections, but who
    connects to whom shuffled (load(shuffle_seed): degree-preserving edge swaps). In the real wiring I2L reaches M1
    directly; in fake brain 1 it reaches the backward neurons DA05/DA08/AVAL and M1 only via AIMR -> URXL. Same
    evolution, same playground: does aiming still appear, how fast, how well?"""
    name = "worm-fake-freefire"
    SHUFFLE = 1

    def __init__(self, shuffle_seed=None, params=None, substeps=6):
        super().__init__(self.SHUFFLE if shuffle_seed is None else shuffle_seed, params, substeps)


class WormFake2FreeFirePlayer(WormFakeFreeFirePlayer):
    """A second, differently shuffled fake brain: one fake brain could be lucky or unlucky."""
    name = "worm-fake2-freefire"
    SHUFFLE = 2


class FreeIOFreeFireV2Player(FreeIOFreeFirePlayer):
    """B without the firing rule, with the 2026-11-03 shell sense (SHELL_OLD=False). First trained with two enemies."""
    name = "free-freefire-v2"
    SHELL_OLD = False
