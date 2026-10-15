"""Save zoomed crops of an arbitrary full-resolution region for chosen frames.

Usage: python -I zoom_region.py <video> <out_png> <y0> <y1> <x0> <x1> <scale> <frame> [...]
"""
import sys

import cv2
import numpy as np

video, out = sys.argv[1], sys.argv[2]
y0, y1, x0, x1 = (int(v) for v in sys.argv[3:7])
scale = float(sys.argv[7])
frames = sorted(int(f) for f in sys.argv[8:])
cap = cv2.VideoCapture(video)
rows, n, want = [], 0, set(frames)
while want:
    ok, f = cap.read()
    if not ok:
        break
    if n in want:
        crop = cv2.resize(f[y0:y1, x0:x1], None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        label = np.zeros((crop.shape[0], 140, 3), np.uint8)
        cv2.putText(label, str(n), (6, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        rows.append(np.hstack([label, crop]))
        want.discard(n)
    n += 1
cv2.imwrite(out, np.vstack(rows))
