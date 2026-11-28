"""Local research test (never committed: derived from game files): a move chain as a clip, recording above, render below.

Usage: python -I clip_chain.py <frames dir> <stem> <character> <work dir of the recording> <attack_windows.csv> <out.mp4>
                               <anim:f0-f1:start_s>...
Each segment plays frames f0..f1 of an animation (posexport .bin files); start_s is when the animation started in the
recording (overlay readings), so the top half shows the recording at start_s + frame/30. The render turns red while a
TAE attack or throw window of that animation is open. 30 frames a second.
Root motion (posexport's <stem>_a<id>_root.csv) is chained across the segments. The camera is a lock-on camera: it
stands behind the player, 2.5 m back and 1.7 m up, and looks at the boss's centre; the player stands 1 m in front of the
boss where the animation named by env WOLF_AT starts (the throw's follow-up), on the boss's starting forward (-Z).
"""
import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np

d, stem, char, work, wins_csv, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5], sys.argv[6]
segs = []
for s in sys.argv[7:]:
    a, fr, st = s.split(":")
    f0, f1 = (int(x) for x in fr.split("-"))
    segs.append((a, f0, f1, float(st)))
T = np.array([[int(r["a"]), int(r["b"]), int(r["c"])] for r in csv.DictReader(open(d / f"{stem}_tris.csv"))], np.int64)
WIN = {}
for r in csv.DictReader(open(wins_csv, encoding="utf-8")):
    if r["character"] == char and r["kind"] in ("attack", "throw"):
        WIN.setdefault(int(r["anim"]), []).append((float(r["start_s"]), float(r["end_s"]), r["kind"]))
track = list(csv.DictReader(open(work / "boss_track.csv", encoding="utf-8")))
times = np.array([float(r["time_s"]) for r in track])
z = np.load(work / "boss_crops.npz")
data, off = z["data"], z["offsets"]
C = 360
FOCAL = (C / 2) / np.tan(np.radians(50) / 2)
ROOT = {a: np.loadtxt(d / f"{stem}_a{a}_root.csv", delimiter=",").reshape(-1, 4, 4) for a, _, _, _ in segs}
bases, B = [], np.eye(4)
for a, f0, f1, st in segs:
    bases.append(B.copy())
    B = ROOT[a][min(f1, len(ROOT[a]) - 1)] @ B
wolf_at = __import__("os").environ.get("WOLF_AT", segs[-1][0])
k = next(i for i, sg in enumerate(segs) if sg[0] == wolf_at)
fwd0 = (np.array([0, 0, -1, 0]) @ bases[k])[:3]
wolf = bases[k][3, :3] + fwd0 / np.linalg.norm(fwd0) * 1.0
CAM = wolf + np.array([0, 0, -1.0]) * 2.5 + np.array([0, 1.7, 0])


def render(V, hot):
    # the game's data is left-handed (the left eye is at +X while the face looks down -Z): mirror X for a
    # right-handed renderer, as DS Anim Studio does
    V = V * np.array([-1, 1, 1], np.float32)
    target = V.mean(0)
    fwd = (target - CAM) / np.linalg.norm(target - CAM)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = V - CAM
    P = np.stack([rel @ right, rel @ up, rel @ fwd], -1)
    tri = P[T]
    keep = tri[:, :, 2].min(1) > 0.1
    tri = tri[keep]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    g = (40 + 190 * (0.25 + 0.75 * np.abs(n[:, 2])))
    xy = np.stack([C / 2 + FOCAL * tri[:, :, 0] / tri[:, :, 2], C / 2 - FOCAL * tri[:, :, 1] / tri[:, :, 2]], -1)
    xy = np.clip(xy, -4 * C, 5 * C).round().astype(np.int32)
    img = np.full((C, C, 3), 255, np.uint8)
    for i in np.argsort(-tri[:, :, 2].mean(1)):
        col = (int(g[i] * 0.55), int(g[i] * 0.55), int(min(255, g[i] * 1.1))) if hot else (int(g[i]),) * 3
        cv2.fillConvexPoly(img, xy[i], col, cv2.LINE_AA)
    return img


vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), 30, (C, 2 * C + 30))
t0, n = time.time(), 0
for (anim, f0, f1, st), base in zip(segs, bases):
    for f in range(f0, f1 + 1, int(__import__("os").environ.get("STRIDE", "1"))):
        at = f / 30
        win = [w for w in WIN.get(int(anim), []) if w[0] - 1 / 60 <= at <= w[1] + 1 / 60]
        V = np.fromfile(d / f"{stem}_a{anim}_f{f}.bin", np.float32).reshape(-1, 3)
        M = ROOT[anim][min(f, len(ROOT[anim]) - 1)] @ base
        V = (np.hstack([V, np.ones((len(V), 1), np.float32)]) @ M)[:, :3]
        i = int(np.argmin(np.abs(times - (st + at))))
        top = cv2.resize(cv2.imdecode(data[off[i]:off[i + 1]], cv2.IMREAD_COLOR), (C, C))
        head = np.full((30, C, 3), 255, np.uint8)
        label = f"{anim[2:]} +{at:.2f}s  rec {st + at:.2f}s" + (f"  {win[0][2]}" if win else "")
        cv2.putText(head, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200) if win else (0, 0, 0), 1, cv2.LINE_AA)
        vw.write(np.vstack([head, top, render(V, bool(win))]))
        n += 1
vw.release()
print(f"wrote {out}: {n} frames in {time.time() - t0:.0f} s")
