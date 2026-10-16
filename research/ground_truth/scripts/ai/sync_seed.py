"""Write the owner's step-8 decisions into the product seed (plan step 8, V3.1 M6).

Usage: python -I sync_seed.py [--check]

Rewrites only the genichiro-ashina boss in backend/seed/bosses.json, from:
    semantic/genichiro_product_moveset.csv   which moves exist, their names and phases (from the decision table)
    semantic/genichiro_content_review.csv    the approved text and move-type changes
Everything else in the boss (name, location, source, phase names) and every other boss stay as they are.

- Moves keep their slugs, so attempts keep pointing at them. A move dropped from the moveset (iaijutsu) disappears from
  the seed; the Alembic migration moves its attempts to the move it merged into and deletes the row.
- A move whose names changed gets name_zh_source "translation"; a Chinese name stays "wiki" only while it is unchanged.
- New moves get the approved move type and no text and no source (owner, 2026-10-15).
- In each phase, moves already listed keep their order; moves new to the phase follow, in moveset order.
--check exits 1 if the seed would change, without writing it.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
SEED = GT.parent.parent / "backend/seed/bosses.json"
BOSS = "genichiro-ashina"
TEXT_FIELDS = ("description", "telegraph", "counter", "common_mistakes")
KEYS = ["id", "name", "name_zh", "name_zh_source", "name_zh_source_url", "move_type", "description", "description_zh",
        "telegraph", "telegraph_zh", "counter", "counter_zh", "common_mistakes", "common_mistakes_zh", "source_name",
        "source_url"]

moveset = list(csv.DictReader(open(GT / "semantic/genichiro_product_moveset.csv", encoding="utf-8")))
review = list(csv.DictReader(open(GT / "semantic/genichiro_content_review.csv", encoding="utf-8")))
pending = [r["key"] for r in review if r["owner_review"] != "通过" and r["field"] != "source_label"]
if pending:
    sys.exit(f"content review rows not approved, decide them first: {', '.join(pending)}")

text = SEED.read_text(encoding="utf-8")
seed = json.loads(text)
boss = next(b for b in seed if b["id"] == BOSS)
current = {}
for p in boss["phases"]:
    for m in p["moves"]:
        current.setdefault(m["id"], m)

moves = {}
for r in moveset:
    old = current.get(r["slug"])
    m = dict(old) if old else {k: None for k in KEYS}
    m["id"] = r["slug"]
    if old is None or (r["name_en"], r["name_zh"]) != (old["name"], old["name_zh"]):
        m["name"], m["name_zh"] = r["name_en"], r["name_zh"]
        m["name_zh_source"], m["name_zh_source_url"] = "translation", None
    moves[r["slug"]] = m
for r in review:
    if r["field"] in TEXT_FIELDS:
        moves[r["slug"]][r["field"]], moves[r["slug"]][r["field"] + "_zh"] = r["new_en"], r["new_zh"]
    elif r["field"] == "move_type":
        moves[r["slug"]]["move_type"] = r["new_zh"]          # the review sheet keeps the type code in this column
missing = [s for s, m in moves.items() if not m["move_type"]]
assert not missing, f"moves without a type: {missing}"

for p in boss["phases"]:
    n = str(p["phase_number"])
    wanted = [r["slug"] for r in moveset if n in r["phases"].split("、")]
    kept = [m["id"] for m in p["moves"] if m["id"] in wanted]
    order = kept + [s for s in wanted if s not in kept]
    p["moves"] = [{k: moves[s][k] for k in KEYS} for s in order]

out = json.dumps(seed, indent=2, ensure_ascii=False) + "\n"
sys.stdout.reconfigure(encoding="utf-8")
if "--check" in sys.argv:
    print("seed is up to date" if out == text else "seed would change")
    sys.exit(0 if out == text else 1)
SEED.write_text(out, encoding="utf-8", newline="\n")
print(f"{BOSS}: {len(moves)} moves; " + "; ".join(f"phase {p['phase_number']}: {len(p['moves'])}" for p in boss["phases"]))
