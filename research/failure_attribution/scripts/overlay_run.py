"""Read the dev-menu overlay of a recording into observations, then check it and make the move answers.

Usage: python -I overlay_run.py <recording id> <work dir> [--from N]

Runs the V3.1 overlay steps (research/ground_truth/scripts/overlay/README.md) and what follows them, step by step,
writing work/<recording id>/overlay_progress.json for the review page's /progress view:

    1-12  templates, the first and second reads, the caches, the line-1 and line 2-5 reads (overlay scripts 1-8)
    13    segments.json (frames with the character line on screen) and the position-specific time reads
    14    occurrences: with the automatic restarts the first time (written to restart_review.csv as "not checked by
          eye"), with restart_review.csv once it exists, so restarts checked by eye are kept
    15    phase bounds, summarize, export to research/ground_truth/observations/<ruleset>/genichiro/<id>/, coverage.
          Phase 1 ends when the deathblow animation (any 012xxx / 013xxx) around the first HUD deathblow ends (the
          animations differ between fights: 012100→012110, 012000, 013100→013110); phase 2 ends at the end of the
          first character-line segment (the cutscene); phase 3 is the next segment
    16    the chain check of every castle recording against the owner-approved AI chains
    17    failure_answers.py for this recording

Before step 1 the work dir needs the TAE ID lists and the whitelist, and labeled.json with about ten frames read by eye
covering all ten digits and both characters (the overlay README). Step 15 needs the recording's HUD events
(hud_pipeline.py). corrections.csv and char_corrections.csv are made empty when missing; reads corrected by eye go
there, and --from 14 rebuilds from them. A misread usually breaks a chain, so step 16 lists where to look.
"""
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, HERE, recordings, video_path, work_dir  # noqa: E402

OVL = GT / "scripts/overlay"
LABELS = ["做数字模板", "第一遍读编号", "第二遍读编号", "缓存叠加层截图", "读角色编号和时间", "二值化读时间",
          "自适应阈值读第 1 行", "缓存第 2–5 行", "读第 2 行", "读第 3 行", "读第 4 行", "读第 5 行",
          "按位置读时间", "合成每次动画", "统计和导出", "动作链核对", "生成招式答案"]
EXPECTED = [15, 300, 300, 240, 60, 60, 60, 300, 60, 60, 60, 60, 90, 30, 20, 20, 20]     # seconds, for the bar


class Progress:
    def __init__(self, rec_id, first):
        self.path = work_dir(rec_id) / "overlay_progress.json"
        old = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() and first > 1 else None
        self.steps = old["steps"] if old else [{"label": label, "status": "waiting", "seconds": 0} for label in LABELS]
        for st in self.steps[first - 1:]:
            st.update(status="waiting", seconds=0)
        self.started = old["started"] if old else time.time()
        self.failed = False

    def set(self, i, status, seconds):
        self.steps[i - 1].update(status=status, seconds=int(seconds))
        self.failed = status == "failed"
        done = sum(e for e, st in zip(EXPECTED, self.steps) if st["status"] == "done")
        run = sum(min(st["seconds"], e) for e, st in zip(EXPECTED, self.steps) if st["status"] == "running")
        data = {"started": self.started, "updated": time.time(), "fraction": (done + run) / sum(EXPECTED),
                "failed": self.failed, "steps": self.steps}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


def run(progress, i, *args):
    """Run one script as step i, updating the progress every few seconds; returns its stdout."""
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, "-I", *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")
    while proc.poll() is None:
        progress.set(i, "running", time.time() - t0)
        time.sleep(3)
    out, err = proc.communicate()
    if proc.returncode:
        progress.set(i, "failed", time.time() - t0)
        sys.exit(f"step {i} ({LABELS[i - 1]}) failed:\n{err[-2000:]}")
    progress.set(i, "done", time.time() - t0)
    print(f"{i:2d} {LABELS[i - 1]}: {(out.strip().splitlines() or [''])[-1][:150]}", flush=True)
    return out


def segments(work):
    r3 = list(csv.DictReader(open(work / "frames3.csv", encoding="utf-8")))
    on = [float(r["char_line_ncc"]) > 0.5 for r in r3]
    segs, i, n = [], 0, len(on)
    while i < n:
        if on[i]:
            j = i
            while j + 1 < n and (on[j + 1] or any(on[j + 2:j + 31])):     # bridge gaps under 30 frames
                j += 1
            segs.append([i, j + 1])
            i = j + 1
        else:
            i += 1
    return [s for s in segs if s[1] - s[0] > 60]


def phase_bounds(rec_id, work, segs):
    fps = json.load(open(work / "video.json"))["fps"]
    blows = [float(e["time_s"]) for e in csv.DictReader(open(work_dir(rec_id) / "events.csv", encoding="utf-8"))
             if e["type"] == "deathblow"]
    occ = list(csv.DictReader(open(work / "occurrences.csv", encoding="utf-8")))
    near = [o for o in occ if blows and 12000 <= int(o["anim"][5:]) < 14000
            and float(o["start_time"]) - 1.0 <= blows[0] <= float(o["end_time"]) + 1.0]
    p1_end = max(int(o["end_frame"]) for o in near) + 1 if near else int((blows[0] if blows else 0) * fps)
    bounds = {"1": [0, p1_end], "2": [p1_end, segs[0][1]]}
    if len(segs) > 1:
        bounds["3"] = [segs[1][0], segs[-1][1]]
    return bounds


def main():
    rec_id, work = sys.argv[1], Path(sys.argv[2])
    first = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 1
    rec = recordings()[rec_id]
    video = video_path(rec)
    out = GT / "observations" / rec.get("ruleset", "vanilla") / "genichiro" / rec_id
    progress = Progress(rec_id, first)
    steps = {1: ("overlay_extract.py", "templates", video, work), 2: ("overlay_extract.py", "extract", video, work),
             3: ("overlay_extract2.py", video, work), 4: ("cache_crops.py", video, work), 5: ("overlay_extract3.py", work),
             6: ("time_read.py", work), 7: ("overlay_extract4.py", work), 8: ("cache_lines.py", video, work)}
    steps.update({8 + k - 1: ("read_line.py", work, f"line{k}_min.npy", f"line{k}.csv") for k in range(2, 6)})
    for i in range(first, 13):
        run(progress, i, OVL / steps[i][0], *steps[i][1:])
    if first <= 13:
        json.dump(segments(work), open(work / "segments.json", "w"))
        run(progress, 13, OVL / "time_read2.py", work)
    if first <= 14:
        for name, header in (("corrections.csv", ["line", "frame", "read", "corrected", "evidence"]),
                             ("char_corrections.csv", ["frame_from", "frame_to", "read", "corrected", "evidence"])):
            if not (work / name).exists():
                with open(work / name, "w", newline="", encoding="utf-8") as fh:
                    csv.writer(fh).writerow(header)
        reviewed = (work / "restart_review.csv").exists()
        text = run(progress, 14, OVL / "occurrences.py", work, work / "restart_sheet.png", 6, 0.15,
                   *([] if reviewed else ["--auto"]))
        if not reviewed:
            with open(work / "restart_review.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["anim", "candidate_frame", "verdict", "exact_frame", "evidence"])
                for m in re.finditer(r"^\s+(a000_\d{6}) (\d+) ", text, re.M):
                    w.writerow([m.group(1), m.group(2), "restart", "", "automatic detection (W=6, drop 0.15); not checked by eye"])
    if first <= 15:
        segs = json.load(open(work / "segments.json"))
        bounds = phase_bounds(rec_id, work, segs)
        json.dump(bounds, open(work / "phase_bounds.json", "w"))
        b = json.dumps(bounds)
        t0 = time.time()
        for args in ((OVL / "summarize.py", work, b), (OVL / "export_observation.py", work, out, b),
                     (OVL / "coverage.py", out, work / "c7100_tae_ids.txt", work / "c7110_tae_ids.txt")):
            r = subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                progress.set(15, "failed", time.time() - t0)
                sys.exit(r.stderr[-2000:])
        progress.set(15, "done", time.time() - t0)
        print(f"15 {LABELS[14]}: phases {bounds}", flush=True)
    if first <= 16:
        chain = GT / "observations" / rec.get("ruleset", "vanilla") / "genichiro"
        run(progress, 16, GT / "scripts/ai/chain_check.py", chain / "chain_check.csv", chain / "chain_check.md")
        rows = [r for r in csv.DictReader(open(chain / "chain_check.csv", encoding="utf-8")) if r["recording"] == rec_id]
        for r in rows:
            if r["verdict"] == "对不上":
                print(f"   unexplained: {r['time']} {r['prev']} -> {r['anim']} ({r['detail']}): look for a misread there")
    run(progress, 17, HERE / "failure_answers.py", rec_id)


if __name__ == "__main__":
    main()
