"""Which senses carry the aiming (2026-11-03, user: "다른 감각들을 조합 이 조합이 어떤건지 궁금하군" / "가짜 뇌 실험에도 영향을
미칠것 같은데"): aim index with groups of senses muted, 12 playground games each. B's aiming survived muting I2 alone and
vanished only with the enemy senses and the shell touch muted together, so single-sense lesions can mislead.
  aim_combo.py run [run ...]"""
import sys
import aim_path as A
P = ("pred_front", "pred_back", "pred_L", "pred_R", "mouth_noxious"); T = ("touch_front", "touch_back", "touch_L", "touch_R")
F = ("smell_up", "smell_down", "mouth_food")
TESTS = [("none", ()), ("I2 (mouth_noxious)", ("mouth_noxious",)), ("enemy 5", P), ("shell touch 4", T), ("enemy+shell 9", P + T),
         ("food 3", F), ("smell 2", ("smell_up", "smell_down"))]
for run in sys.argv[1:]:
    for name, mute in TESTS:
        r = A.games(run, mute)
        print(f"{run:20s} mute {name:20s} fire ahead {r['fire_ahead']:.2f} ({r['ahead_steps']}) else {r['fire_else']:.3f} | kills {r['kills']:.2f} score {r['score']:.0f}", flush=True)
