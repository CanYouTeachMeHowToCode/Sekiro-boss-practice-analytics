"""Lightning reversals that cost HP (owner's rule of 2026-11-13); the rule is analysis/sekiro_analysis/reversal.py.

Usage:
    python -I reversal.py template                      cut the glyph template (local, like the other game images)
    python -I reversal.py scan <recording id | all>     score every damage event of the recordings
    python -I reversal.py apply <recording id>          scan, then mark the reversals in events.csv (hud_pipeline.py)
    python -I reversal.py probe <video> <t0> <t1>       the glyph score of every third frame between t0 and t1

The template is cut from the English clip at 3:22.5 (SOURCE) and kept in work/content/glyph_dalei.npy (the worker gets
a copy in its data folder).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, video_path, work_dir  # noqa: E402
from sekiro_analysis import reversal as rv  # noqa: E402
from sekiro_analysis.reversal import warm_map  # noqa: E402

TEMPLATE = WORK / "content" / "glyph_dalei.npy"
SOURCE = ("不同情景测试录像/英文弦一郎.mp4", 202.5, (280, 460, 1220, 1360))   # file, second, y0 y1 x0 x1 at 2560×1440


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


def glyph():
    return rv.Glyph(np.load(TEMPLATE))


def scan(rec_id, g):
    rv.scan(video_path(recordings()[rec_id]), work_dir(rec_id), g)


def apply(rec_id, g):
    rv.apply(video_path(recordings()[rec_id]), work_dir(rec_id), g)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "template":
        build_template()
    elif sys.argv[1] == "probe":
        g = glyph()
        for t, s in rv.scores(Path(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), g):
            print(f"{t:7.2f} {s:.3f}")
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], glyph())
    elif sys.argv[1] == "scan":
        g = glyph()
        for rid in (list(recordings()) if sys.argv[2] == "all" else [sys.argv[2]]):
            if (work_dir(rid) / "events.csv").exists():
                scan(rid, g)
