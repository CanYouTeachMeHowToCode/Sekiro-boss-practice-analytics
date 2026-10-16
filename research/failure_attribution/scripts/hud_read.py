"""Read Wolf's HP and posture from the game HUD.

Usage:
    python -I hud_read.py cache  <video> <cache.npz> [--step N]   decode once, keep per-column HUD colours
    python -I hud_read.py series <cache.npz> <out.csv>             HP, posture and HUD visibility per frame

The cache keeps, for every N-th frame (default 2), the median HSV colour of each column of the two HUD strips, so
thresholds can be tuned without decoding the video again. Frames go through mask_overlay() first, like everywhere in
the pipeline, although these strips never touch the overlay.

Geometry, measured at 2560×1440 and scaled to other resolutions:
    HP bar       rows 1304–1314, x 148–980 (left edge to right end cap)
    posture bar  rows 1238–1247, x 1280 ± 290; a white pin marks the centre (± 6)
Colours (OpenCV HSV, H 0–179):
    HP           red: H <= 12 or >= 168, S >= 70, V >= 80; just lost (pale): S <= 45, V >= 120; empty track: V <= 70
    posture      the posture is the bright part growing from the centre: V >= 140, S >= 120, warm hue (H <= 35 or
                 >= 170). It turns from yellow (H ≈ 25) to orange-red (H ≈ 13) as it fills. The track around it is
                 dimmer (V ≈ 70–130), orange or red.
The output columns: frame, time_s, hud (HP bar on screen), hp, hp_lost (0..1 of the bar), posture_bar (posture bar on
screen), posture (0..1 of PO_HALF).
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overlay_mask import BASE_H, BASE_W, mask_overlay  # noqa: E402

HP_ROWS, HP_X0, HP_X1 = (1304, 1314), 148, 980
PO_ROWS, PO_CX, PO_HALF, PIN = (1238, 1247), 1280, 290, 6


def columns(frame, rows, x0, x1):
    h, w = frame.shape[:2]
    sx, sy = w / BASE_W, h / BASE_H
    part = frame[int(rows[0] * sy):int(rows[1] * sy) + 1, int(x0 * sx):int(x1 * sx)]
    part = cv2.resize(part, (x1 - x0, part.shape[0]), interpolation=cv2.INTER_AREA) if sx != 1 else part
    return np.median(cv2.cvtColor(part, cv2.COLOR_BGR2HSV), axis=0).astype(np.uint8)


def cache(video, out, step):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames, hp, po = [], [], []
    n = 0
    while cap.grab():
        if n % step == 0:
            ok, frame = cap.retrieve()
            frame = mask_overlay(frame)
            frames.append(n)
            hp.append(columns(frame, HP_ROWS, HP_X0, HP_X1))
            po.append(columns(frame, PO_ROWS, PO_CX - PO_HALF, PO_CX + PO_HALF))
        n += 1
    np.savez_compressed(out, frame=np.array(frames), fps=fps, hp=np.stack(hp), posture=np.stack(po))
    print(f"{n} frames, {len(frames)} cached from {video}")


def run_from(mask, start, max_gap=4):
    """Length of the run of True values from `start`, allowing short gaps."""
    end, gaps = start, 0
    for x in range(start, mask.size):
        if mask[x]:
            end, gaps = x + 1, 0
        else:
            gaps += 1
            if gaps > max_gap:
                break
    return end - start


def read_hp(cols):
    h, s, v = (cols[:, i].astype(int) for i in range(3))
    red = ((h <= 12) | (h >= 168)) & (s >= 70) & (v >= 80)
    pale = (s <= 45) & (v >= 120)
    dark = v <= 70
    n = red.size
    hp = run_from(red, 0)
    lost = run_from(pale, hp) if hp < n else 0
    hud = (red | pale | dark).mean() >= 0.9
    return hud, hp / n, lost / n


def read_posture(cols):
    h, s, v = (cols[:, i].astype(int) for i in range(3))
    c = PO_HALF
    fill = (v >= 140) & (s >= 120) & ((h <= 35) | (h >= 170))
    right = run_from(fill, c + PIN)
    left = run_from(fill[::-1], c + PIN)
    reach = min(left, right)            # the bar grows symmetrically; the shorter side resists stray colour
    return reach > 2, (PIN + reach) / PO_HALF if reach > 2 else 0.0


def series(cache_file, out):
    d = np.load(cache_file)
    fps = float(d["fps"])
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "time_s", "hud", "hp", "hp_lost", "posture_bar", "posture"])
        for n, hp_cols, po_cols in zip(d["frame"], d["hp"], d["posture"]):
            hud, hp, lost = read_hp(hp_cols)
            bar, posture = read_posture(po_cols) if hud else (False, 0.0)
            w.writerow([int(n), f"{n / fps:.3f}", int(hud), f"{hp:.4f}", f"{lost:.4f}", int(bar), f"{posture:.4f}"])
    print(f"wrote {out}")


if __name__ == "__main__":
    if sys.argv[1] == "cache":
        step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 2
        cache(sys.argv[2], sys.argv[3], step)
    else:
        series(sys.argv[2], sys.argv[3])
