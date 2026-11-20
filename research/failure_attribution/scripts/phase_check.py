"""Version 4 development check: the phase read from the HUD (phase_read.py) against the deathblow count of version 3.

Usage: python -I phase_check.py scan <recording id ...|all>   phase_read.scan() of each into PHASE_DIR/<id>/
       python -I phase_check.py compare [--work <dir>]         at every event of every scanned recording, the phase of
                                                              version 3 (its events.csv in the work folder) and of
                                                              version 4; every difference listed
       python -I phase_check.py dist [--work <dir>]            the second dot's lit share and the names read, by the
                                                              version-3 phase, to see how far apart they are

On the owner's recordings version 3's phases are right (every sure move right, the phase-3 moves told apart), so version
4 must give the same phase at every event there; recording 2 of the test server, where version 3 missed every deathblow,
is checked on the server (numbers only). hud_phase.csv files are derived from the videos and stay local, outside the
repository (PHASE_DIR); --work names the work folder that holds version 3's events.csv (default: this checkout's).
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, video_path, work_dir  # noqa: E402
from sekiro_analysis import content_check, moves, phase_read  # noqa: E402

PHASE_DIR = Path.home() / ".sekiro-research" / "v4" / "phase"


def work_of(rec_id):
    if "--work" in sys.argv:
        return Path(sys.argv[sys.argv.index("--work") + 1]) / rec_id
    return work_dir(rec_id)


def scan(ids):
    recs = recordings()
    templates = content_check.load_templates(WORK / "content" / "name_templates.npz")
    for rec_id in (list(recs) if ids == ["all"] else ids):
        out = PHASE_DIR / rec_id
        if (out / "hud_phase.csv").exists():
            continue
        try:
            video = video_path(recs[rec_id])
        except (KeyError, FileNotFoundError) as exc:
            print(f"{rec_id}: no video ({exc})")
            continue
        if not Path(video).exists():
            print(f"{rec_id}: no video at {video}")
            continue
        out.mkdir(parents=True, exist_ok=True)
        phase_read.scan(video, out, templates, overlay=bool(recs[rec_id].get("overlay")))
        print(f"{rec_id}: scanned", flush=True)


def events(rec_id):
    path = work_of(rec_id) / "events.csv"
    return list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else None


def compare():
    total, differ, fallback = 0, [], 0
    for out in sorted(PHASE_DIR.iterdir()):
        evs = events(out.name)
        if evs is None:
            print(f"{out.name}: no events.csv in the work folder")
            continue
        hud = phase_read.load(out)
        blows = [float(e["time_s"]) for e in evs if e["type"] == "deathblow"]
        ends = [float(e["time_s"]) for e in evs if e["type"] == "death" and e["note"].startswith("not resurrected")]
        for e in evs:
            if e["type"] not in ("damage", "posture_break", "death"):
                continue
            t = float(e["time_s"])
            v3 = moves.phase_at(t, blows, ends)
            v4 = phase_read.phase_at(t, hud, v3)
            total += 1
            seen = (hud["t"] < t) & (hud["t"] >= t - phase_read.LOOKBACK_S) & (hud["dot1"] >= phase_read.LIT_FRACTION)
            fallback += not seen.any()
            if v4 != v3:
                differ.append(f"{out.name} {e['key']}: version 3 phase {v3}, version 4 {v4}")
    print(f"{total} events, {len(differ)} with another phase, {fallback} with no HUD sample (deathblow count)")
    print("\n".join(differ))


def dist():
    by = {1: [], 2: [], 3: []}
    names = {1: Counter(), 2: Counter(), 3: Counter()}
    for out in sorted(PHASE_DIR.iterdir()):
        evs = events(out.name)
        if evs is None:
            continue
        rows = list(csv.DictReader(open(out / "hud_phase.csv", encoding="utf-8")))
        blows = [float(e["time_s"]) for e in evs if e["type"] == "deathblow"]
        ends = [float(e["time_s"]) for e in evs if e["type"] == "death" and e["note"].startswith("not resurrected")]
        for r in rows:
            t = float(r["time_s"])
            if float(r["dot1"]) < phase_read.LIT_FRACTION:
                continue
            p = moves.phase_at(t, blows, ends)
            if p not in by or any(abs(t - b) < 3 for b in blows):        # the moments around a deathblow are mixed
                continue
            by[p].append(float(r["dot2"]))
            score = float(r["name_score"]) if r["name_score"] else None
            names[p][r["name"] if score is not None and score >= phase_read.NAME_MIN else "-"] += 1
    for p in (1, 2, 3):
        x = sorted(by[p])
        if x:
            q = lambda f: x[min(len(x) - 1, int(f * len(x)))]  # noqa: E731
            print(f"phase {p}: {len(x)} samples, dot2 lit share min {x[0]:.2f} p1 {q(0.01):.2f} median {q(0.5):.2f} "
                  f"p99 {q(0.99):.2f} max {x[-1]:.2f}; names {dict(names[p])}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "scan":
        scan([a for a in sys.argv[2:] if not a.startswith("--")])
    else:
        {"compare": compare, "dist": dist}[cmd]()
