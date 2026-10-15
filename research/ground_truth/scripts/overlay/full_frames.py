"""Save downscaled full frames, and report how much the whole picture changes across a frame range.

Usage: python -I full_frames.py <video> <out_png> <diff_from> <diff_to> <frame> [...]
"""
import sys

import cv2
import numpy as np

video, out, d0, d1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
frames = sorted(int(f) for f in sys.argv[5:])
cap = cv2.VideoCapture(video)
keep, prev, diffs, n = [], None, [], 0
last = max(frames + [d1])
while n <= last:
    ok, f = cap.read()
    if not ok:
        break
    if d0 <= n <= d1:
        small = cv2.resize(f, (320, 180)).astype(np.float32)
        if prev is not None:
            diffs.append((n, float(np.abs(small - prev).mean())))
        prev = small
    if n in frames:
        img = cv2.resize(f, (960, 540))
        cv2.putText(img, f"frame {n} ({n / 59.995:.2f}s)", (10, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        keep.append(img)
    n += 1
if diffs:
    v = np.array([d for _, d in diffs])
    print(f"whole-frame change {d0}-{d1}: mean {v.mean():.2f}, max {v.max():.2f}, frames with change<0.3: {(v < 0.3).sum()}/{len(v)}")
if len(keep) % 2:
    keep.append(np.zeros_like(keep[0]))
cv2.imwrite(out, np.vstack([np.hstack(keep[i:i + 2]) for i in range(0, len(keep), 2)]))
