"""List the attack, projectile and 危 windows of every c7100 / c7110 animation, from the TAE dumps.

Usage: python -I attack_windows.py <tae_dir> <out.csv>

    tae_dir   tae_dump.py output: c7100_tae.json, c7110_tae.json (local, never committed)

One row per TAE event that can hurt Wolf or marks 危, with its time inside the animation:
    attack    InvokeAttackBehavior (type 1) with a behavior judge ID >= 0; -1 is an empty event
    bullet    InvokeBulletBehavior (type 2) with a judge ID >= 0 outside 980–989: the projectile is fired at start_s
              (arrows, lightning) and hits later
    peril     InvokeBulletBehavior with a judge ID in 980–989: the red 危 kanji, which hurts no one
    throw     Throw Atk (type 304) with a judge ID >= 0: the damage of a throw that has caught Wolf, in the follow-up the
              game plays after the catch, not one the AI requests (c7100 4100 after the grab 3020, c7110 4110 after
              3009; owner, 2026-11-27). Version 5: V3.1 counted only attack and projectile events, so these were missed
`hit` numbers the distinct attack and throw windows of an animation as catalog.py counts them (overlapping or touching
windows are one hit), so a row can say "the 6th hit of 3092". Entries that import another entry's events
(import_other_anim) get that entry's windows. The failure attribution uses this table to tell which animation was
hitting at the moment Wolf lost HP; it is derived metadata (identifiers and times), not game assets.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from throws import THROW_ATK  # noqa: E402

tae_dir, out = sys.argv[1:3]
rows = []
for c in ("c7100", "c7110"):
    tae = json.load(open(f"{tae_dir}/{c}_tae.json", encoding="utf-8"))["animations"]
    by = {a["id"]: a for a in tae}
    for a in tae:
        src = a
        while src["kind"] == "import_other_anim":
            src = by[src["imports_from"]]
        found = []
        for e in src["events"]:
            judge = e["params"].get("BehaviorJudgeID", -1)
            if e["type"] == 1 and judge >= 0:
                kind = "attack"
            elif e["type"] == THROW_ATK and judge >= 0:
                kind = "throw"
            elif e["type"] == 2 and judge >= 0:
                kind = "peril" if 980 <= judge <= 989 else "bullet"
            else:
                continue
            found.append((kind, judge, e["start_s"], e["end_s"], e["start_frame_30"], e["end_frame_30"]))
        found.sort(key=lambda x: (x[2], x[3], x[0]))
        hit, end = 0, None
        for kind, judge, s, en, sf, ef in found:
            n = ""
            if kind in ("attack", "throw"):
                if end is None or sf > end:
                    hit += 1
                    end = ef
                else:
                    end = max(end, ef)
                n = hit
            rows.append({"character": c, "anim": a["id_int"], "kind": kind, "judge": judge, "hit": n,
                         "start_s": f"{s:.4f}", "end_s": f"{en:.4f}"})

rows.sort(key=lambda r: (r["character"], r["anim"], float(r["start_s"]), r["kind"]))
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["character", "anim", "kind", "judge", "hit", "start_s", "end_s"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out}: {len(rows)} windows in {len({(r['character'], r['anim']) for r in rows})} animations")
