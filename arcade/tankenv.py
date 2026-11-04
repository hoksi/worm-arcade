"""Super Tank as an environment: a real MAME (desktop build, with Lua) driven frame by frame through bridge.lua.

Each Env starts its own headless MAME (no throttle, lockstep) with bridge.lua on its own port, so several games can run
at once for training. The game is read from the screen pixels (4 colours: yellow = our tank + border, red = enemy
tanks + small mines, green = wall blocks) plus three RAM values (score, tanks left, game flag).

    env = Env(9141); obs = env.reset(); obs, reward, done = env.step(dir_index, fire); env.close()
dir_index: 0 none, 1 up, 2 up-right, 3 right, 4 down-right, 5 down, 6 down-left, 7 left, 8 up-left.
"""
import os, socket, subprocess, time
import numpy as np
from scipy import ndimage

ROOT = os.path.dirname(os.path.abspath(__file__))
ROMS = os.path.join(ROOT, "..", "roms")      # put supertnk.zip here yourself (from mamedev.org; not in the repository, see README)
FIELD = (32, 224, 10, 246)                     # playfield inside the yellow border (y0, y1, x0, x1), rotated screen
DIRS = [(), ("P1 Up",), ("P1 Up", "P1 Right"), ("P1 Right",), ("P1 Down", "P1 Right"), ("P1 Down",),
        ("P1 Down", "P1 Left"), ("P1 Left",), ("P1 Up", "P1 Left")]
MOVES = ["P1 Up", "P1 Down", "P1 Left", "P1 Right"]
RAM0 = 0x1965                                   # one peek covers reserve (0x1965), score (0x196A-B) and the game flag (0x1A00)
# 0x1A00 = 1 from the start of a real game through its game-over screen, 0 in the attract demo. (Until 2026-11-01 this
# used 0x19B5, which drops to 0 when the bottom bar runs out and a second enemy arrives: every game was cut there,
# ~275-375 steps, while the last tank was still alive; the user noticed the watched worm "stop" at that moment.)
GAME_FLAG = 0x1A00


def _die_with_parent():
    """MAME gets SIGKILL when the Python process that started it dies (a pool worker ends): otherwise it stays behind,
    spinning in lockstep waiting for a "run" that never comes (seen after the first smoke test, 2026-10-31)."""
    import ctypes
    ctypes.CDLL("libc.so.6").prctl(1, 9)          # PR_SET_PDEATHSIG, SIGKILL


class Bridge:
    """Line protocol to bridge.lua (see bridge.lua for the commands)."""

    def __init__(self, sock):
        self.sock, self.buf = sock, b""

    def _line(self):
        while b"\n" not in self.buf:
            d = self.sock.recv(65536)
            if not d:
                raise ConnectionError("bridge closed")
            self.buf += d
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode()

    def _exact(self, n):
        while len(self.buf) < n:
            d = self.sock.recv(max(65536, n - len(self.buf)))
            if not d:
                raise ConnectionError("bridge closed")
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def cmd(self, line, reply=True):
        self.sock.sendall((line + "\n").encode())
        return self._line() if reply else None

    def pix(self):
        head = self.cmd("pix").split()
        w, h, n = int(head[1]), int(head[2]), int(head[3])
        return w, h, self._exact(n)


def parse(w, h, data):
    """Raw BGRA pixels -> dict of objects in the rotated playfield."""
    a = np.frombuffer(data, np.uint8).reshape(h, w, 4)
    a = np.rot90(a, k=-1)                                       # Super Tank is a vertical game: turn clockwise
    y0, y1, x0, x1 = FIELD
    f = a[y0:y1, x0:x1]
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    yel = (r > 150) & (g > 150) & (b < 100)
    red = (r > 150) & (g < 80) & (b < 80)
    grn = (g > 150) & (r < 100)
    out = {"player": None, "enemies": [], "mines": [], "walls": grn}      # "shells" are split off from mines in Env
    if yel.sum() > 15:
        ys, xs = np.nonzero(yel)
        out["player"] = (float(xs.mean()), float(ys.mean()))
    lab, n = ndimage.label(ndimage.binary_dilation(red, iterations=1))
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        cnt = int((lab[sl] == i).sum())
        cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
        (out["enemies"] if cnt > 40 else out["mines"]).append((cx, cy))
    return out


class Env:
    def __init__(self, port, game="supertnk", frames_per_step=4):
        self.port, self.k = port, frames_per_step
        env = dict(os.environ, ARCADE_PORT=str(port))
        tag = f"{ROOT}/run/env{port}"
        os.makedirs(tag, exist_ok=True)
        self.proc = subprocess.Popen(
            ["nice", "-n", "10", "mame", game, "-rompath", ROMS, "-video", "none", "-sound", "none", "-skip_gameinfo",
             "-nothrottle", "-cfg_directory", f"{tag}/cfg", "-nvram_directory", f"{tag}/nvram", "-state_directory", f"{tag}/st",
             "-autoboot_script", f"{ROOT}/bridge.lua"], cwd=tag, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, preexec_fn=_die_with_parent)
        for _ in range(200):
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=60)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("bridge did not open")
        self.b = Bridge(s)
        self.b.cmd("sync 1")
        self.held = set()
        self.run(300)                                            # boot past the logo
        self.b.cmd("save _boot"); self.run(1)                    # clean start point for reboot()

    def run(self, n):
        return self.b.cmd(f"run {n}")

    def hold(self, names):
        names = set(names)
        for f in self.held - names:
            self.b.cmd(f"set 0 {f}")
        for f in names - self.held:
            self.b.cmd(f"set 1 {f}")
        self.held = names

    def ram(self):
        raw = bytes.fromhex(self.b.cmd(f"peek {RAM0} {GAME_FLAG - RAM0 + 1}").split()[1])
        return {"reserve": raw[0], "score": (raw[5] * 256 + raw[6]) * 10, "playing": raw[GAME_FLAG - RAM0] == 1,
                "second_enemy": raw[0x19B5 - RAM0] != 128}

    def observe(self):
        o = parse(*self.b.pix())
        o.update(self.ram())
        # mines never move; a small red thing that was not there one step ago is a shell
        prev = getattr(self, "_mines", [])
        o["shells"] = [m for m in o["mines"] if not any(abs(m[0] - q[0]) + abs(m[1] - q[1]) < 1 for q in prev)]
        o["mines"] = [m for m in o["mines"] if m not in o["shells"]]
        self._mines = o["mines"] + o["shells"]
        return o

    def reboot(self, frames=1):
        """Back to the state saved right after boot. Needed after loading a mid-game save state (the dodge drills):
        reset() from there returned a frozen game (reserve 0, score 0, flag still 1) that never ended, and the v6 run
        of 2026-11-01 evolved toward those 5000-step, 0-point non-games for 7 generations."""
        self.b.cmd("load _boot"); self.run(1); self.b.cmd("release"); self.held = set(); self._mines = []
        self.run(max(1, frames))

    def reset(self):
        """Coin, then start twice (the first press only leaves the title), until a real game is on."""
        self.hold([])
        for _ in range(5):
            for name in ("Coin 1", "1 Player Start", "1 Player Start"):
                self.hold([name]); self.run(10); self.hold([]); self.run(60)
            for _ in range(10):
                self.run(30)
                o = self.observe()
                if o["playing"]:
                    self.last = o
                    return o
        raise RuntimeError("game did not start")

    def step(self, d, fire):
        self.hold(list(DIRS[d]) + (["P1 Button 1"] if fire else []))
        self.run(self.k)
        o = self.observe()
        reward = o["score"] - self.last["score"]
        died = o["reserve"] < self.last["reserve"]
        self.last = o
        return o, reward, (not o["playing"]), died

    def close(self):
        try:
            self.b.cmd("exit")
        except (OSError, ConnectionError):
            pass
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
