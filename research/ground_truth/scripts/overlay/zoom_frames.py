"""Save zoomed overlay crops (character line + animation line) for chosen frames.

Usage: python -I zoom_frames.py <video> <out_png> <frame> [<frame> ...]
"""
import sys

import cv2
import numpy as np

video, out, frames = sys.argv[1], sys.argv[2], sorted(int(f) for f in sys.argv[3:])
cap = cv2.VideoCapture(video)
rows, n = [], 0
want = set(frames)
while want:
    ok, f = cap.read()
    if not ok:
        break
    if n in want:
        crop = f[80:185, 120:600]
        crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        label = np.zeros((crop.shape[0], 160, 3), np.uint8)
        cv2.putText(label, str(n), (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        rows.append(np.hstack([label, crop]))
        want.discard(n)
    n += 1
cv2.imwrite(out, np.vstack(rows))
