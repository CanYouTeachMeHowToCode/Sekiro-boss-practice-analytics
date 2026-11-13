"""Find the white lock-on dot that Sekiro draws on the locked-on boss.

The dot is a flat white disc about 13 px across at 2560×1440 (V 200–245, low saturation, sharp edge), usually on the
boss's chest. Candidates come from a disc template matched on the half-size grey frame; each is then checked at full
size: the inner disc must be bright, even and unsaturated, and brighter than the ring around it. A tracker prefers the
candidate near the previous dot, so sparks, petals and snow far away lose to the real dot.

Searched area: everything but the HUD at the bottom (y >= SEARCH_BOTTOM), the top-left corner with the boss HP bar and
deathblow markers, and the masked overlay box. Coordinates are in 2560×1440 pixels; other 16:9 sizes are scaled.
"""
import cv2
import numpy as np

from overlay_mask import BASE_H, BASE_W

SEARCH_BOTTOM, CORNER = 1150, (720, 380)          # rows below are HUD; the top-left corner holds the boss bar
R_IN, R_OUT = (0, 4), (9, 13)                     # inner disc and surrounding ring, full-size pixels
MIN_NCC, MIN_IN_V, MAX_IN_SD, MAX_IN_S, MIN_CONTRAST = 0.55, 175, 30, 80, 35
TRACK_RADIUS, JUMP_NCC = 260, 0.75                # a dot far from the last one needs a better match


def _disc(radius, size):
    yy, xx = np.mgrid[:size, :size] - size // 2
    return (np.hypot(xx, yy) <= radius).astype(np.float32)


TEMPLATE = (_disc(3.3, 15) * 255).astype(np.uint8)   # half size: the 13 px dot is ~6.5 px
_YY, _XX = np.mgrid[-14:15, -14:15]
_RR = np.hypot(_XX, _YY)
IN_MASK = (_RR >= R_IN[0]) & (_RR <= R_IN[1])
RING_MASK = (_RR >= R_OUT[0]) & (_RR <= R_OUT[1])


def candidates(frame, k=8):
    """Up to k candidate dots: (ncc, x, y) in full-size pixels of this frame, best first."""
    h, w = frame.shape[:2]
    sx, sy = w / BASE_W, h / BASE_H
    small = cv2.resize(frame, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    grey = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    ncc = cv2.matchTemplate(grey, TEMPLATE, cv2.TM_CCOEFF_NORMED)
    off = TEMPLATE.shape[0] // 2
    ncc[int(SEARCH_BOTTOM * sy / 2) - off:, :] = -1
    ncc[:int(CORNER[1] * sy / 2), :int(CORNER[0] * sx / 2)] = -1
    out = []
    for _ in range(k):
        _, best, _, (x, y) = cv2.minMaxLoc(ncc)
        if best < MIN_NCC:
            break
        out.append((float(best), (x + off) * 2, (y + off) * 2))
        ncc[max(0, y - 6):y + 7, max(0, x - 6):x + 7] = -1
    return out


def check(frame, x, y):
    """Refine a candidate at full size; returns (x, y) of the disc centre, or None if it is not a lock-on dot."""
    h, w = frame.shape[:2]
    best = None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = x + dx, y + dy
            if not (14 <= cx < w - 14 and 14 <= cy < h - 14):
                continue
            patch = frame[cy - 14:cy + 15, cx - 14:cx + 15]
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            v_in, s_in, v_ring = hsv[..., 2][IN_MASK], hsv[..., 1][IN_MASK], hsv[..., 2][RING_MASK]
            score = float(v_in.mean()) - float(v_ring.mean())
            ok = (v_in.mean() >= MIN_IN_V and v_in.std() <= MAX_IN_SD and s_in.mean() <= MAX_IN_S
                  and score >= MIN_CONTRAST)
            if ok and (best is None or score > best[0]):
                best = (score, cx, cy)
    return (best[1], best[2]) if best else None


class Tracker:
    FORGET = 30                                   # calls without a dot before the last position stops counting

    def __init__(self):
        self.last, self.missing = None, 0

    def __call__(self, frame):
        """(x, y, ncc) of the lock-on dot in this frame, or None."""
        found = []
        for ncc, x, y in candidates(frame):
            pos = check(frame, x, y)
            if pos:
                found.append((ncc, *pos))
        if not found:
            self.missing += 1
            if self.missing > self.FORGET:
                self.last = None
            return None
        self.missing = 0
        if self.last is not None:
            near = [f for f in found if np.hypot(f[1] - self.last[0], f[2] - self.last[1]) <= TRACK_RADIUS]
            if near:
                pick = max(near, key=lambda f: f[0] - 0.001 * np.hypot(f[1] - self.last[0], f[2] - self.last[1]))
            else:
                pick = max(found)
                if pick[0] < JUMP_NCC:
                    return None
        else:
            pick = max(found)
        self.last = (pick[1], pick[2])
        return pick[1], pick[2], pick[0]
