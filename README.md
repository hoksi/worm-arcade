# Worm Arcade

[한국어](README.ko.md)

**▶ Live: https://hoksi.github.io/worm-arcade/**

A *C. elegans* worm plays the 1981 arcade game **Super Tank**. Its brain is the worm's real wiring diagram, unchanged; only a few numbers per neuron, such as how strongly it signals, were trained by evolution.

Without the ROM file, the game page shows a recording of a game the worm really played. Choose the Super Tank ROM file (supertnk.zip, free from [mamedev.org](https://www.mamedev.org/roms/supertnk/)) on the page and it runs right in your browser, nothing to install. The ROM is not included in this repository.

- [Game](https://hoksi.github.io/worm-arcade/) — the worm plays the real game in MAME (WebAssembly): a video, or live with your ROM
- [Worm Lab](https://hoksi.github.io/worm-arcade/lab.html) — put out food and predators and watch how the worm moves, compare two worms side by side, silence neurons

## How it works

```
screen → senses → C. elegans brain (448 neurons and muscles) → motor neurons → buttons
```

1. **Reading the screen** — yellow = own tank, red = enemies and shells, green = mines (food). `web/play.js`
2. **Senses** — the game becomes 13 senses fed into sensory neurons: odour rising / falling, enemy ahead / behind / left / right, touch from shells and side walls, nose against the wall, food in front of the mouth, enemy straight ahead.
3. **Brain** — the OpenWorm connectome (Cook et al. 2019). Each neuron is one graded value; evolution sets each neuron's output strength and bias plus three action thresholds. No connection is changed. `web/brain.js`
4. **Actions** — forward neurons (AVB, VB, DB) minus backward neurons (AVA, VA, DA) move the tank, dorsal vs ventral head-bending neurons turn it, and the pharynx's spitting neurons (M1, pm3) fire the cannon.

Training happens in a Python playground modelled on the real game, about 40 times faster, so 500 generations are practical. Scores are then measured in the real game.

Two ways to connect the game to the worm; with free wiring, evolution also chooses the links between the game and the neurons:

| | fixed | free |
| --- | --- | --- |
| game → senses | hand-picked neurons (enemy → ASH) | evolved |
| motor neurons → buttons | hand-picked neurons (AVA → reverse) | evolved |

## Some results

Mean of 12 real games, 200 points per enemy:

| model | real game | fires when an enemy is straight ahead / otherwise |
| --- | --- | --- |
| green (free wiring, no firing rule) | 2,788 | 70% / 3% |
| blue (fixed wiring, no firing rule) | 2,225 | 69% / 3% |
| random buttons | ~1,771 | — |

With no "fire only at an enemy straight ahead" rule, both learned to do exactly that. The fixed worm uses the pharynx's own I2 → M1 wiring; the free worm combines the enemy-direction senses with shell touch.

Scores vary a lot with luck: two worms trained the same way averaged 2,321 and 1,875 in the real game. So the gaps in the table alone don't show which approach is better.

## Run it yourself

```bash
# pages
cd docs && python3 -m http.server 8000      # http://localhost:8000 (choose the ROM on the page)

# check the JS against the Python reference
cd web && node brain.test.cjs && node play.test.cjs && node free.test.cjs

# evolve a worm in the playground (Python 3, numpy, scipy)
cd worm && python3 pg_evolve.py --sym --predator --kill-pts 200 --player free_freefire --out my_worm --steps 1500 --gens 500
python3 exp_report.py my_worm                # 12 playground games
python3 aim_combo.py my_worm                 # which senses carry the aiming
# training also writes worm/run/my_worm/best.web.json, the model for the browser;
# to show it on the pages, copy it to docs/models/my_worm.json and add a line to docs/models/index.json
python3 ../web/i18n_pages.py                 # rebuild the English pages after editing the Korean ones

# score in the real game (needs a desktop MAME with Lua; put supertnk.zip in roms/ yourself)
cd arcade && python3 score_real.py out.json my_worm

# build MAME for the browser
mame/build.sh /path/to/emsdk
```

- `worm/` — brain, senses, playground (1–2 predators), evolution, analysis
- `web/` — browser brain and screen reader, parity tests
- `arcade/` — real-game link: a Lua bridge running inside MAME, an environment that reads the screen and RAM, 12-game real scoring
- `mame/` — MAME 0.285 WebAssembly build script and patch ([build guide](mame/README.md))
- `docs/` — GitHub Pages

## Credits and licences

- Our code (`worm/`, `web/`, `docs/*.html`, `docs/*.js`): MIT — [LICENSE](LICENSE)
- **Super Tank** © 1981 Video Games GmbH. The ROM images were made available for free, non-commercial use by Reinhard Stompe, founder of Video Games GmbH: https://www.mamedev.org/roms/supertnk/ . mamedev.org is approved to distribute them on its own site only, so the ROM is not in this repository or on the page; a ROM chosen on the page is used only inside that browser. This is a non-commercial personal experiment; it will be taken down at the rights holder's request.
- **MAME** 0.285 (`docs/mame/supertnk.js`, `.wasm`): GPL-2.0-or-later, source https://github.com/mamedev/mame/tree/mame0285 , our changes in [`mame/`](mame/).
- **Connectome**: OpenWorm c302 `herm_full_edgelist.csv` (Cook et al. 2019, *Nature* 571), MIT — https://github.com/openworm/c302
