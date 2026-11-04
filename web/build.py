"""Build docs/lab.ko.html: brain.js and the exported JSON inlined into index.src.html (one self-contained page)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "lab.ko.html")      # the Korean source page; i18n_pages.py makes lab.html
base = json.load(open(f"{HERE}/base.json"))
src = open(f"{HERE}/index.src.html").read()
js = open(f"{HERE}/brain.js").read()
play = open(f"{HERE}/play.js").read()
data = json.dumps({"base": base, "params": {}}, ensure_ascii=False, separators=(",", ":"))   # models: fetched from models/ at run time
assert "</script" not in data and "</script" not in js
assert "</script" not in play
out = src.replace("/*BRAIN_JS*/", js).replace("/*PLAY_JS*/", play).replace("/*DATA_JSON*/", data)
open(OUT, "w").write(out)
print(OUT, len(out) // 1024, "KB")
