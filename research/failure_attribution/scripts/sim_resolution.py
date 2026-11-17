"""Simulated resolutions (V4 M3): the frozen analyzer on labelled test recordings scaled down to 1080p and 720p.

Usage: python -I sim_resolution.py make        scale the recordings and register the copies
       python -I sim_resolution.py run         hud_pipeline.py on every copy, then compare
       python -I sim_resolution.py compare     every size against the owner's answers of the original (see compare())
       python -I sim_resolution.py refs720     the 720p reference library from the development recordings
       python -I sim_resolution.py eval720     predict the 720p videos with it and score them

Before the analyzer is packaged for the upload worker, this shows whether it holds up at the resolutions M3 accepts
(16:9, 720p to 4K): the HUD positions are scaled from 2560×1440, the 死 mask was made at 1440p, and the boss crops are
matched against references that are all 1440p, so a smaller picture could lose events or moves. The copies are the
owner's test recordings scaled with ffmpeg (area filter, H.264 CRF 18, the bundled binary of imageio-ffmpeg), so they
keep the owner's labels; the game rendering at a lower resolution, and other recording software, can still differ,
which only real clips show.

The copies go to SIM_DIR (local, outside the repository) and into recordings.local.json (gitignored), with set
"simulation" and answers_of the original, so reliability.py reads the original's answers (common.annotation_dir).
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FA, HERE, recordings, video_path, work_dir  # noqa: E402

SIM_DIR = Path.home() / ".sekiro-research" / "sim_resolution"
SOURCES = ["2026-11-11-castle-1", "2026-11-11-castle-2", "2026-11-11-castle-6", "2026-11-11-castle-8"]
SIZES = [(1920, 1080), (1280, 720)]
LOCAL = FA / "recordings.local.json"


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make():
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    recs = recordings()
    entries = []
    for src in SOURCES:
        rec = recs[src]
        for w, h in SIZES:
            out = SIM_DIR / f"{src}-{h}p.mp4"
            if not out.exists():
                subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path(rec)),
                                "-vf", f"scale={w}:{h}:flags=area", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                                "18", "-pix_fmt", "yuv420p", "-an", str(out)], check=True)
            entries.append({"id": f"{src}-{h}p", "file_name": str(out), "ruleset": rec["ruleset"],
                            "game_version": rec["game_version"], "overlay": False, "set": "simulation",
                            "answers_of": src, "use": f"{src} scaled to {w}×{h} by sim_resolution.py"})
            print(f"{out.name}: {out.stat().st_size / 1e6:.0f} MB", flush=True)
    LOCAL.write_text(json.dumps({"recordings": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run():
    ids = [r for r, rec in recordings().items() if rec.get("set") == "simulation"]
    for rec_id in ids:
        subprocess.run([sys.executable, "-I", str(HERE / "hud_pipeline.py"), rec_id], check=True)
    compare()


def events_of(keys):
    """(type, seconds) of event keys such as damage@28.2 or missed:damage@12.34."""
    return [(k.split("@")[0].split(":")[-1], float(k.split("@")[1])) for k in keys]


def compare(tol=0.35):
    """Every size of every source against the owner's answers of the original recording, matched by time.

    reliability.py matches the owner's review to the detected events by key, which only works on the recording the
    owner reviewed: on a copy, an event detected a little earlier or not at all simply falls out of the answers. Here the
    answers are the original's real failures (Recording.truth), and a reported failure of a copy is the same failure when
    one of its events has the type and, within tol seconds, the time of one of the answer's events."""
    from reliability import Recording
    recs = recordings()
    answers = {src: Recording(src, recs[src]).truth for src in SOURCES}
    lines, misses = [], []
    for label, suffix in [("1440p", "")] + [(f"{h}p", f"-{h}p") for _, h in SIZES]:
        tot = dict(truth=0, found=0, reported=0, real=0, merged=0, split=0, n=0, sure=0, sure_right=0, top1=0, top3=0)
        for src in SOURCES:
            truth = answers[src]
            preds = []
            for r in csv.DictReader(open(work_dir(src + suffix) / "failure_predictions.csv", encoding="utf-8")):
                preds.append({"t": float(r["time_s"]), "events": events_of(r["events"].split()), "sure": r["certain"] == "1",
                              "top": [c.rsplit(":", 1)[0] for c in r["candidates"].split()]})
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
                     f"{pc(tot['top1'], tot['n'])} | {pc(tot['top3'], tot['n'])} |")
    print("| size | failures found | reported are real | merged | split | sure | sure right | first right | in top 3 |")
    print("|---|---|---|---|---|---|---|---|---|")
    print("\n".join(lines))
    print()
    print("\n".join(misses))


REF_DIR = SIM_DIR / "ref720"


def refs720():
    """The 720p reference library: every development recording scaled to 1280×720 like the copies above, registered with
    set "reference-720p" (move_match.library() uses it for videos of 720p or less), and its boss crops and features.
    A copy keeps its original's events (same timeline) and, for a dev-menu recording, its overlay animations
    (Rec.references follows answers_of). Steps already done are skipped, so the job can be run again after a stop."""
    import shutil
    recs = recordings()
    local = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {"recordings": []}
    have = {e["id"] for e in local["recordings"]}
    REF_DIR.mkdir(parents=True, exist_ok=True)
    devs = [(j, r) for j, r in recs.items() if r.get("set") == "development" and not r.get("answers_of")]
    for k, (j, rec) in enumerate(devs, 1):
        cid, out = f"{j}-720p", REF_DIR / f"{j}-720p.mp4"
        if not out.exists():
            tmp = out.with_name(out.stem + ".part.mp4")
            subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path(rec)), "-vf",
                            "scale=1280:720:flags=area", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-an", str(tmp)], check=True)
            tmp.replace(out)
        if cid not in have:
            local["recordings"].append({"id": cid, "file_name": str(out), "ruleset": rec["ruleset"],
                                        "game_version": rec["game_version"], "overlay": bool(rec.get("overlay")),
                                        "set": "reference-720p", "answers_of": j,
                                        "use": f"{j} scaled to 1280×720: the 720p reference library"})
            LOCAL.write_text(json.dumps(local, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            have.add(cid)
        w = work_dir(cid)
        w.mkdir(parents=True, exist_ok=True)
        if not (w / "events.csv").exists():
            shutil.copy(work_dir(j) / "events.csv", w / "events.csv")
        if not (w / "boss_crops.npz").exists():
            subprocess.run([sys.executable, "-I", str(HERE / "boss_track.py"), cid], check=True)
        if not (w / "boss_feats_small14.npy").exists():
            subprocess.run([sys.executable, "-I", str(HERE / "boss_features.py"), cid], check=True)
        print(f"[{k}/{len(devs)}] {cid} ready", flush=True)


def eval720():
    """Predict the 720p videos again (move_match picks the 720p library now) and score them: the four scaled test
    recordings against their originals' answers, the owner's real 720p clip (2026-11-17-castle-4) in the scenario
    report. The predictions made with the 1440p library are kept as failure_predictions_lib1440.csv."""
    import shutil
    queries = [f"{s}-720p" for s in SOURCES] + ["2026-11-17-castle-4"]
    for q in queries:
        pred = work_dir(q) / "failure_predictions.csv"
        keep = work_dir(q) / "failure_predictions_lib1440.csv"
        if pred.exists() and not keep.exists():
            shutil.copy(pred, keep)
        subprocess.run([sys.executable, "-I", str(HERE / "move_match.py"), "predict", q], check=True)
    compare()
    subprocess.run([sys.executable, "-I", str(HERE / "reliability.py"), "report", "--set", "scenario"], check=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"make": make, "run": run, "compare": compare, "refs720": refs720, "eval720": eval720}[sys.argv[1]]()
