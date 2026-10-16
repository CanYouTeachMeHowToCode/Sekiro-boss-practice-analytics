"""Measure the overlay font pitch: column profile of the animation line for chosen frames.

Usage: python -I pitch_probe.py <video> <out_png> <frame> [...]
"""
import sys

import cv2
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
from overlay_extract import LINE_X0, LINE_X1, LINE_Y0, LINE_Y1, text_mask

video, out, frames = sys.argv[1], sys.argv[2], sorted(int(f) for f in sys.argv[3:])
cap = cv2.VideoCapture(video)
rows, n, want = [], 0, set(frames)
while want:
    ok, f = cap.read()
    if not ok:
        break
    if n in want:
        m = text_mask(f[LINE_Y0:LINE_Y1, LINE_X0:LINE_X1])
        img = cv2.cvtColor((m * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        img = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        for k in range(30):          # predicted cell boundaries at pitch 14 from x=95-6*14
            x = (95 + (k - 6) * 14) * 4
            if 0 <= x < img.shape[1]:
                cv2.line(img, (x, 0), (x, img.shape[0]), (0, 0, 255) if k % 5 else (0, 255, 0), 1)
        rows.append(img)
        cols = m.sum(axis=0)
        on = np.where(cols > 0)[0]
        # left edges of glyph column runs
        edges = [int(x) for i, x in enumerate(on) if i == 0 or on[i - 1] != x - 1]
        print(n, "glyph left edges:", edges)
        want.discard(n)
    n += 1
cv2.imwrite(out, np.vstack(rows))
