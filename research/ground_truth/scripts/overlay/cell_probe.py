"""Print the min-channel values of chosen ID cells (to see how background text leaks into the mask).

Usage: python -I cell_probe.py <video> <frame> <cell_index> [<frame> <cell_index> ...]
"""
import sys

import cv2
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
from overlay_extract import CELL_Y0, CELL_Y1, ID_PITCH, ID_X0, LINE_X0, LINE_Y0

video = sys.argv[1]
pairs = [(int(sys.argv[i]), int(sys.argv[i + 1])) for i in range(2, len(sys.argv), 2)]
cap = cv2.VideoCapture(video)
want = {f for f, _ in pairs}
n = 0
np.set_printoptions(linewidth=250)
while want:
    ok, f = cap.read()
    if not ok:
        break
    if n in want:
        for ff, k in pairs:
            if ff != n:
                continue
            x0 = LINE_X0 + ID_X0 + k * ID_PITCH
            cell = f[LINE_Y0 + CELL_Y0: LINE_Y0 + CELL_Y1, x0: x0 + ID_PITCH].min(axis=2)
            print(f"frame {n} cell {k}: min-channel /10")
            for row in cell:
                print(" ".join(f"{v // 10:2d}" for v in row))
        want.discard(n)
    n += 1
