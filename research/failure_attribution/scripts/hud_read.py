"""Read Wolf's HP and posture from the game HUD.

Usage:
    python -I hud_read.py cache  <video> <cache.npz> [--step N]   decode once, keep per-column HUD colours
    python -I hud_read.py series <cache.npz> <out.csv>             HP, posture and HUD visibility per frame

The cache keeps, for every N-th frame (default 2), the median HSV colour of each column of the HUD strips, so
thresholds can be tuned without decoding the video again. The hue median is taken with the hue rotated by 90, since red
sits at both ends of the range; caches built before this was fixed read some red columns as cyan and must be rebuilt.
Frames go through mask_overlay() first, like everywhere in the pipeline, although these strips never touch the overlay.

Geometry, measured at 2560×1440 and scaled to other resolutions:
    HP bar       rows 1304–1314, x 148–980 (left edge to right end cap)
    posture bar  rows 1238–1247, x 1280 ± 290; a white pin marks the centre (± 6)
    boss HP bar  rows 122–142, x 151–695, top left under the deathblow markers. Only rows 124–131 are read: in the
                 dev-menu recordings the overlay's "[Active Anime]" header (left visible on purpose) crosses the lower
                 rows.
Colours (OpenCV HSV, H 0–179):
    HP           red: H <= 12 or >= 168, S >= 70, V >= 80; just lost (pale): S <= 45, V >= 120; empty track: V <= 70
    boss HP      red: H <= 12 or >= 168, S >= 70, V >= 70; just lost (pale): S <= 45, V >= 90; empty track: V <= 70.
                 Wolf's deathblow takes all the remaining HP at once: the red goes pale, then drains.
    posture      the posture is the bright part growing from the centre: V >= 140, S >= 120, warm hue (H <= 35 or
                 >= 170). It turns from yellow (H ≈ 25) to orange-red (H ≈ 13) as it fills. The track around it is
                 dimmer (V ≈ 70–130), orange or red. The ends of the bar taper to a point, so a full bar can read as
                 little as 0.84.
    break line   when Wolf's posture breaks, the bar turns for a few tenths of a second into a thin bright red line
                 about twice its width, without the end chevrons (rows ≈ 1242–1251, reaching x 1280 ± 450 or further).
                 A full bar cleared by Wolf's own deathblow or at a resurrection only turns dark red and keeps its
                 shape and chevrons (± 290). The line is measured where the normal bar never reaches, x 1280 ± 340–450,
                 on rows 1243–1250, against rows 1232–1239 just above: red hue (H >= 165 or <= 6), S >= 100, V >= 75,
                 and at least 30 brighter or 50 more saturated than the rows above, so it shows in dark scenes and on
                 snow.
The output columns: frame, time_s, hud (HP bar on screen), hp, hp_lost (0..1 of the bar), posture_bar (posture bar on
screen), posture (0..1 of PO_HALF), break_line (share of line-coloured columns on the weaker side, 0..1), boss_bar
(boss HP bar on screen), boss_hp, boss_lost (0..1 of the bar).
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
LINE_ROWS, ABOVE_ROWS, LINE_IN, LINE_OUT = (1243, 1250), (1232, 1239), 340, 450
BOSS_ROWS, BOSS_X0, BOSS_X1 = (124, 131), 151, 695


def columns(frame, rows, x0, x1):
    h, w = frame.shape[:2]
    sx, sy = w / BASE_W, h / BASE_H
    part = frame[int(rows[0] * sy):int(rows[1] * sy) + 1, int(x0 * sx):int(x1 * sx)]
    part = cv2.resize(part, (x1 - x0, part.shape[0]), interpolation=cv2.INTER_AREA) if sx != 1 else part
    hsv = cv2.cvtColor(part, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[..., 0] = (hsv[..., 0] + 90) % 180        # red sits at both ends of the hue range (0 and 179): rotate it to the
    med = np.median(hsv, axis=0)                   # middle so a column of 178s and 1s does not have a median of 90
    med[:, 0] = (med[:, 0] + 90) % 180
    return med.astype(np.uint8)


def cache(video, out, step):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames, hp, po, line, boss = [], [], [], [], []
    n = 0
    while cap.grab():
        if n % step == 0:
            ok, frame = cap.retrieve()
            frame = mask_overlay(frame)
            frames.append(n)
            hp.append(columns(frame, HP_ROWS, HP_X0, HP_X1))
            po.append(columns(frame, PO_ROWS, PO_CX - PO_HALF, PO_CX + PO_HALF))
            sides = [(PO_CX - LINE_OUT, PO_CX - LINE_IN), (PO_CX + LINE_IN, PO_CX + LINE_OUT)]
            line.append(np.vstack([np.hstack([columns(frame, LINE_ROWS, a, b), columns(frame, ABOVE_ROWS, a, b)])
                                   for a, b in sides]))
            boss.append(columns(frame, BOSS_ROWS, BOSS_X0, BOSS_X1))
        n += 1
    np.savez_compressed(out, frame=np.array(frames), fps=fps, hp=np.stack(hp), posture=np.stack(po), line=np.stack(line),
                        boss=np.stack(boss))
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


def read_boss(cols):
    h, s, v = (cols[:, i].astype(int) for i in range(3))
    red = ((h <= 12) | (h >= 168)) & (s >= 70) & (v >= 70)
    pale = (s <= 45) & (v >= 90)
    dark = v <= 70
    n = red.size
    hp = run_from(red, 0)
    lost = run_from(pale, hp) if hp < n else 0
    return (red | pale | dark).mean() >= 0.9, hp / n, lost / n


def read_line(cols):
    h, s, v, s_above, v_above = (cols[:, i].astype(int) for i in (0, 1, 2, 4, 5))
    red = ((h >= 165) | (h <= 6)) & (s >= 100) & (v >= 75) & ((v - v_above >= 30) | (s - s_above >= 50))
    half = red.size // 2
    return min(red[:half].mean(), red[half:].mean())


def series(cache_file, out):
    d = np.load(cache_file)
    if "line" not in d or "boss" not in d:
        sys.exit(f"{cache_file} has no break-line or boss HP strip: rebuild it (hud_pipeline.py <id> --recache)")
    fps = float(d["fps"])
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "time_s", "hud", "hp", "hp_lost", "posture_bar", "posture", "break_line", "boss_bar", "boss_hp",
                    "boss_lost"])
        for n, hp_cols, po_cols, line_cols, boss_cols in zip(d["frame"], d["hp"], d["posture"], d["line"], d["boss"]):
            hud, hp, lost = read_hp(hp_cols)
            bar, posture = read_posture(po_cols) if hud else (False, 0.0)
            line = read_line(line_cols) if hud else 0.0
            boss_bar, boss_hp, boss_lost = read_boss(boss_cols)
            w.writerow([int(n), f"{n / fps:.3f}", int(hud), f"{hp:.4f}", f"{lost:.4f}", int(bar), f"{posture:.4f}",
                        f"{line:.3f}", int(boss_bar), f"{boss_hp:.4f}" if boss_bar else "0.0000",
                        f"{boss_lost:.4f}" if boss_bar else "0.0000"])
    print(f"wrote {out}")


if __name__ == "__main__":
    if sys.argv[1] == "cache":
        step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 2
        cache(sys.argv[2], sys.argv[3], step)
    else:
        series(sys.argv[2], sys.argv[3])
