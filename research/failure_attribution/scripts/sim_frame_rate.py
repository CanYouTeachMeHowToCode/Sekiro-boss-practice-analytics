"""Simulated 30 fps (version 3, 2026-11-18): the labelled 60 fps test recordings with every other frame dropped.

Usage: python -I sim_frame_rate.py make        drop every other frame of the sources and register the copies
       python -I sim_frame_rate.py run         hud_pipeline.py on every copy (the version in this checkout), then compare
       python -I sim_frame_rate.py compare     every copy against the owner's answers of its original (as sim_resolution)

A development check, not a measurement: a copy keeps every other frame, so version 3, reading every frame of it, sees
nearly the same moments version 2 sees reading every other frame of the original. It shows that the 30 fps path
(sampling.py) works, and what re-encoding at 30 fps changes; it cannot show how real 30 fps recordings behave (other
recorders, bitrates, a game capped at 30). Real tester footage at 30 fps is held out of development (owner,
2026-11-18); the measurement is on new 30 fps fights labelled blind after version 3 is frozen (plan_m2.md protocol).

The copies are the version-2 test recordings (测试录像13–21) through ffmpeg's fps filter: a constant 30 fps on the
original's own timeline, the frame nearest each 30th of a second (mostly every other frame), and where the recorder
dropped a frame the one before it repeated, as a constant-rate recorder does. Encoded as sim_resolution.py does (H.264
CRF 18, the bundled binary of imageio-ffmpeg), at their own size. They go to SIM_DIR (local, outside the repository) and
into recordings.local.json (gitignored), with set "simulation-fps" and answers_of the original.

The pipeline times a frame as frame / fps, and the owner's answers are on that scale. Where a recorder dropped frames
the two scales part: 测试录像13's recorder kept 4 frames in its last 1.25 s, so it averages 59.52 fps, and frame / fps
runs ahead of its timestamps by up to 1.1 s (0.8%). A copy's frame / 30 is its timestamp, so compare() maps the copy's
times to the original's frame / fps (original_time()) before matching; without that, 7 of 测试录像13's failures were
counted as missed and reported at the wrong time (first two runs, 2026-11-18).
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FA, HERE, recordings, video_path, work_dir  # noqa: E402
from sim_resolution import events_of, ffmpeg  # noqa: E402

SIM_DIR = Path.home() / ".sekiro-research" / "sim_frame_rate"
SOURCES = [f"2026-11-11-castle-{i}" for i in range(1, 10)]
SUFFIX = "-30fps"
SET = "simulation-fps"
LOCAL = FA / "recordings.local.json"


def make():
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    recs = recordings()
    entries = []
    for src in SOURCES:
        rec = recs[src]
        out = SIM_DIR / f"{src}{SUFFIX}.mp4"
        if not out.exists():
            subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path(rec)),
                            "-vf", "fps=30", "-c:v", "libx264", "-preset",
                            "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)], check=True)
        entries.append({"id": src + SUFFIX, "file_name": str(out), "ruleset": rec["ruleset"],
                        "game_version": rec["game_version"], "overlay": False, "set": SET, "answers_of": src,
                        "use": f"{src} with every other frame dropped (30 fps) by sim_frame_rate.py"})
        print(f"{out.name}: {out.stat().st_size / 1e6:.0f} MB", flush=True)
    data = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {"recordings": []}
    keep = [r for r in data["recordings"] if r.get("set") != SET]
    LOCAL.write_text(json.dumps({"recordings": keep + entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run():
    for src in SOURCES:
        subprocess.run([sys.executable, "-I", str(HERE / "hud_pipeline.py"), src + SUFFIX], check=True)
    compare()


def frame_times(video):
    """The video's frame timestamps in seconds, sorted (ffmpeg's mkvtimestamp_v2 muxer: packets only, no decoding)."""
    fd, tmp = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(video), "-map", "0:v:0", "-c", "copy", "-f",
                        "mkvtimestamp_v2", tmp], check=True)
        lines = Path(tmp).read_text(encoding="ascii").splitlines()
    finally:
        os.remove(tmp)
    return np.sort([float(x) / 1000 for x in lines if x.strip() and not x.startswith("#")])


def original_time(src):
    """A function from a time in src's copy (its timestamp) to src's frame / fps: the original's frame nearest that
    timestamp, over the frame rate the pipeline reads (CAP_PROP_FPS)."""
    video = video_path(recordings()[src])
    pts = frame_times(video)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    def to(t):
        i = int(np.clip(np.searchsorted(pts, t), 1, len(pts) - 1))
        return (i if abs(pts[i] - t) < abs(pts[i - 1] - t) else i - 1) / fps
    return to


def predictions(rec_id, to=None):
    """rec_id's failure_predictions.csv; `to` (optional) maps its times to another time scale."""
    to = to or (lambda t: t)
    path = work_dir(rec_id) / "failure_predictions.csv"
    return [{"t": to(float(r["time_s"])), "events": [(a, to(x)) for a, x in events_of(r["events"].split())],
             "sure": r["certain"] == "1",
             "top": [c.rsplit(":", 1)[0] for c in r["candidates"].split()],
             "scores": [float(c.rsplit(":", 1)[1]) for c in r["candidates"].split()]}
            for r in csv.DictReader(open(path, encoding="utf-8"))]


def compare(tol=0.35):
    """The originals (60 fps) and the copies (30 fps) against the owner's answers of the originals, matched by time as
    in sim_resolution.compare(), the copies' times mapped to the originals' frame / fps (original_time())."""
    from reliability import Recording
    recs = recordings()
    answers = {src: Recording(src, recs[src]).truth for src in SOURCES}
    lines, misses = [], []
    for label, suffix in [("60 fps (original)", ""), ("30 fps (copy)", SUFFIX)]:
        tot = dict(truth=0, found=0, reported=0, real=0, merged=0, split=0, n=0, sure=0, sure_right=0, top1=0, top3=0,
                   none=0)
        for src in SOURCES:
            truth, preds = answers[src], predictions(src + suffix, original_time(src) if suffix else None)
            tev = [events_of(t["events"]) for t in truth]
            links = [[i for i, te in enumerate(tev) if any(a == b and abs(x - y) <= tol for a, x in p["events"] for b, y in te)]
                     for p in preds]
            by_truth = {}
            for j, ls in enumerate(links):
                for i in ls:
                    by_truth.setdefault(i, []).append(j)
            tot["truth"] += len(truth)
            tot["found"] += len(by_truth)
            tot["reported"] += len(preds)
            tot["real"] += sum(1 for ls in links if ls)
            tot["merged"] += sum(1 for ls in links if len(ls) > 1)
            tot["split"] += sum(1 for js in by_truth.values() if len(js) > 1)
            tot["none"] += sum(1 for p in preds if p["scores"] and max(p["scores"]) <= -1)
            for i, t in enumerate(truth):
                js = by_truth.get(i, [])
                if not js:
                    misses.append(f"{label} {src} {t['t']:.1f}s missed ({t['row']['move']})")
                    continue
                if len(js) != 1 or len(links[js[0]]) != 1 or not t["moves"]:
                    continue
                pr = preds[js[0]]
                tot["n"] += 1
                tot["sure"] += pr["sure"]
                tot["sure_right"] += pr["sure"] and bool(set(pr["top"][:1]) & t["moves"])
                tot["top1"] += bool(set(pr["top"][:1]) & t["moves"])
                tot["top3"] += bool(set(pr["top"][:3]) & t["moves"])
            for j, ls in enumerate(links):
                if not ls:
                    misses.append(f"{label} {src} {preds[j]['t']:.1f}s reported, no such failure")
        pc = lambda a, b: f"{a}/{b} = {a / b:.0%}" if b else "-"  # noqa: E731
        lines.append(f"| {label} | {pc(tot['found'], tot['truth'])} | {pc(tot['real'], tot['reported'])} | {tot['merged']} | "
                     f"{tot['split']} | {pc(tot['sure'], tot['n'])} | {pc(tot['sure_right'], tot['sure'])} | "
                     f"{pc(tot['top1'], tot['n'])} | {pc(tot['top3'], tot['n'])} | {tot['none']} |")
    print("| video | failures found | reported are real | merged | split | sure | sure right | first right | in top 3 |"
          " nothing comparable |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(lines))
    print()
    print("\n".join(misses))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"make": make, "run": run, "compare": compare}[sys.argv[1]]()
