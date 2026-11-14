"""Lightning reversals that cost HP (V4 M3, owner's rule of 2026-11-13).

Usage:
    python -I reversal.py template                      cut the glyph template (local, like the other game images)
    python -I reversal.py scan <recording id | all>     score every damage event of the recordings
    python -I reversal.py apply <recording id>          scan, then mark the reversals in events.csv (hud_pipeline.py)
    python -I reversal.py probe <video> <t0> <t1>       the glyph score of every third frame between t0 and t1

The owner's rule: Wolf can take a little damage when he catches Genichiro's lightning in the air and sends it back. That
is a successful Lightning Reversal, not a failure. It shows on Genichiro: within a second or two of the hit, the golden
glyph 打雷 floats over him (English game, 3:21.8–3:23.5 of 不同情景测试录像/英文弦一郎.mp4). A damage event followed by the
glyph within WINDOW seconds is a reversal and does not count as a failure.

The glyph is pale gold (H ≈ 20–27, S ≈ 25–40, V ≈ 220–250) and its size changes with the distance to the camera. A frame
is scaled to 1280×720 and the region above the HUD bars searched with the template at several scales (normalised
cross-correlation on a map of how warm and bright each pixel is), so a white flash, snow or the blue-white lightning
itself scores low.

Writes work/<recording id>/reversals.csv: key, time_s, score and glyph_s (the best frame's score and time), run_s
(the longest stretch scoring at least RUN_T) and reversal (1 when run_s >= MIN_RUN).
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, video_path, work_dir  # noqa: E402
from overlay_mask import mask_overlay  # noqa: E402

TEMPLATE = WORK / "content" / "glyph_dalei.npy"
SOURCE = ("不同情景测试录像/英文弦一郎.mp4", 202.5, (280, 460, 1220, 1360))   # file, second, y0 y1 x0 x1 at 2560×1440
W, H = 1280, 720
SEARCH_Y = (0, 590)                       # at 1280×720: everything above Wolf's posture and HP bars
SCALES = (0.6, 0.75, 0.9, 1.1, 1.3, 1.6, 2.0)
WINDOW = (0.3, 3.0)                       # seconds after the HP drop
RUN_T, MIN_RUN, GAP = 0.65, 0.5, 2        # the glyph stays: scores >= RUN_T for MIN_RUN s, gaps of GAP samples
ISOLATION = 3.0                           # the glyph's warmth against the ring around it


def warm_map(frame):
    """0..1 per pixel: bright and warm (gold, cream), low for white, grey-blue sky and saturated orange fire."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    warm = np.clip(1 - np.abs(h - 23) / 12, 0, 1)
    tint = np.clip((s - 12) / 18, 0, 1) * np.clip((80 - s) / 30, 0, 1)
    bright = np.clip((v - 170) / 50, 0, 1)
    return warm * tint * bright


def prepare(frame):
    return cv2.resize(mask_overlay(frame), (W, H), interpolation=cv2.INTER_AREA)


def build_template():
    from content_check import recordings_dir
    name, t, (y0, y1, x0, x1) = SOURCE
    cap = cv2.VideoCapture(str(recordings_dir() / name))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * cap.get(cv2.CAP_PROP_FPS)))
    ok, f = cap.read()
    m = warm_map(f[y0:y1, x0:x1])
    ys, xs = np.nonzero(m > 0.2)
    tpl = m[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]
    tpl = cv2.resize(tpl, (tpl.shape[1] // 2, tpl.shape[0] // 2), interpolation=cv2.INTER_AREA)   # to 1280×720
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    np.save(TEMPLATE, tpl.astype(np.float32))
    print(f"template {tpl.shape[1]}×{tpl.shape[0]} at 1280×720 -> {TEMPLATE}")


class Glyph:
    def __init__(self):
        tpl = np.load(TEMPLATE)
        self.tpls = [cv2.resize(tpl, (max(int(tpl.shape[1] * s), 6), max(int(tpl.shape[0] * s), 12)),
                                interpolation=cv2.INTER_AREA) for s in SCALES]

    def score(self, frame):
        m = warm_map(prepare(frame))[SEARCH_Y[0]:SEARCH_Y[1]]
        if m.max() < 0.3:
            return 0.0
        best = 0.0
        for t in self.tpls:
            r = cv2.matchTemplate(m, t, cv2.TM_CCOEFF_NORMED)
            # a window with (almost) nothing warm in it has no variance and a meaningless correlation: drop it
            th, tw = t.shape
            mean = cv2.boxFilter(m, -1, (tw, th), normalize=True, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
            mean2 = cv2.boxFilter(m * m, -1, (tw, th), normalize=True, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
            std = np.sqrt(np.maximum(mean2 - mean * mean, 0))[:r.shape[0], :r.shape[1]]
            r[(std < 0.05) | ~np.isfinite(r)] = 0
            y, x = np.unravel_index(int(r.argmax()), r.shape)
            # the glyph floats alone: a ring around it, as wide as half the glyph, is far less warm than the glyph
            # itself, unlike a lightning flash or a sunlit patch, which is warm all round
            inside = m[y:y + th, x:x + tw].mean()
            y0, y1, x0, x1 = max(y - th // 2, 0), y + th + th // 2, max(x - tw // 2, 0), x + tw + tw // 2
            outer = m[y0:y1, x0:x1]
            ring = (outer.sum() - m[y:y + th, x:x + tw].sum()) / max(outer.size - th * tw, 1)
            if inside > ISOLATION * ring:
                best = max(best, float(r.max()))
        return best


def scores(video, t0, t1, glyph, every=3):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    i = int(max(t0, 0) * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    out = []
    while i <= t1 * fps:
        ok, f = cap.read()
        if not ok:
            break
        if i % every == 0:
            out.append((i / fps, glyph.score(f)))
        i += 1
    return out


def longest_run(samples):
    """Seconds of the longest stretch of samples scoring >= RUN_T, allowing gaps of up to GAP samples."""
    best, start, miss = 0.0, None, 0
    for t, s in samples:
        if s >= RUN_T:
            start = t if start is None else start
            miss = 0
            best = max(best, t - start)
        elif start is not None:
            miss += 1
            if miss > GAP:
                start = None
    return best


def scan(rec_id, glyph):
    rec = recordings()[rec_id]
    events = [e for e in csv.DictReader(open(work_dir(rec_id) / "events.csv", encoding="utf-8")) if e["type"] == "damage"]
    rows = []
    for e in events:
        t = float(e["time_s"])
        samples = scores(video_path(rec), t + WINDOW[0], t + WINDOW[1], glyph)
        best = max(samples, key=lambda x: x[1], default=(t, 0.0))
        run = longest_run(samples)
        rows.append({"key": e["key"], "time_s": e["time_s"], "score": f"{best[1]:.3f}", "glyph_s": f"{best[0]:.2f}",
                     "run_s": f"{run:.2f}", "reversal": int(run >= MIN_RUN)})
    with open(work_dir(rec_id) / "reversals.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "time_s", "score", "glyph_s", "run_s", "reversal"],
                           lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    top = sorted(rows, key=lambda r: -float(r["run_s"]))[:3]
    print(f"{rec_id}: {len(rows)} damage events, {sum(r['reversal'] for r in rows)} reversals; longest runs "
          + ", ".join(f"{r['key']} {r['run_s']} s (max {r['score']})" for r in top), flush=True)


def apply(rec_id, glyph):
    """Score the damage events of work/<id>/events.csv (scan) and turn the reversals into type "reversal", key
    reversal@<s>, so that nothing downstream counts them as failures. events.csv is rewritten only when a reversal was
    found, so a recording without one keeps the file byte for byte."""
    path = work_dir(rec_id) / "events.csv"
    scan(rec_id, glyph)
    found = {r["key"] for r in csv.DictReader(open(work_dir(rec_id) / "reversals.csv", encoding="utf-8"))
             if r["reversal"] == "1"}
    if not found:
        return
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    fields = list(rows[0].keys())
    renamed = {}
    for e in rows:
        if e["type"] == "damage" and e["key"] in found:
            new = "reversal@" + e["key"].split("@", 1)[1]
            renamed[e["key"]] = new
            e["type"], e["key"] = "reversal", new
            e["note"] = " ".join(x for x in (e["note"], "lightning reversal: the 打雷 glyph showed on Genichiro") if x)
    for e in rows:                                  # a death or break linked to a renamed event
        e["linked"] = " ".join(renamed.get(k, k) for k in e["linked"].split())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{rec_id}: {len(renamed)} damage events are lightning reversals: {' '.join(renamed.values())}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "template":
        build_template()
    elif sys.argv[1] == "probe":
        g = Glyph()
        for t, s in scores(Path(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), g):
            print(f"{t:7.2f} {s:.3f}")
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], Glyph())
    elif sys.argv[1] == "scan":
        g = Glyph()
        for rid in (list(recordings()) if sys.argv[2] == "all" else [sys.argv[2]]):
            if (work_dir(rid) / "events.csv").exists():
                scan(rid, g)
