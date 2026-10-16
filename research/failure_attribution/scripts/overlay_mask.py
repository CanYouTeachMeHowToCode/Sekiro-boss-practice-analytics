"""Mask the dev-menu overlay's live animation lines before any frame reaches the attribution pipeline.

Usage (check image):  python -I overlay_mask.py <video> <seconds> <out.png>

The dev menu's "[Active Anime]" lines show the boss's current animation IDs, which are the answer the pipeline must
find on its own. Every frame read for detection, matching, training or evaluation goes through mask_overlay();
only the scripts that build the answer set read the overlay itself.

What stays visible (owner decision, 2026-10-16): the "[Active Anime]" header and everything above it, including the
character line (c7100 / c7110) and the boss HP bar with its deathblow markers, since the phase is visible in the video
anyway. What is masked: the animation lines below the header, with room for two more lines than were ever seen (five).

Coordinates are measured at 2560×1440 (research/ground_truth/scripts/overlay/README.md: dev menu at its default
top-left position) and scaled to other resolutions.
"""
import sys

import numpy as np

BASE_W, BASE_H = 2560, 1440
# x0, y0, x1, y1 at 2560×1440. The header's bottom edge is at y ≈ 157 and the boss HP bar ends at y ≈ 150; animation
# line 1 starts at y ≈ 158, the fifth ends at y ≈ 292, and the text spans x ≈ 130–500.
MASK = (100, 154, 560, 360)


def mask_box(width: int, height: int) -> tuple[int, int, int, int]:
    sx, sy = width / BASE_W, height / BASE_H
    x0, y0, x1, y1 = MASK
    return int(x0 * sx), int(y0 * sy), int(np.ceil(x1 * sx)), int(np.ceil(y1 * sy))


def mask_overlay(frame: np.ndarray) -> np.ndarray:
    """Returns a copy of the frame with the overlay's animation lines painted black."""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = mask_box(w, h)
    out = frame.copy()
    out[y0:y1, x0:x1] = 0
    return out


if __name__ == "__main__":
    import cv2

    video, t, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    assert ok, "could not read the frame"
    h, w = frame.shape[:2]
    crop = (slice(0, int(420 * h / BASE_H)), slice(0, int(900 * w / BASE_W)))
    before, after = frame[crop], mask_overlay(frame)[crop]
    cv2.imwrite(out, np.vstack([before, np.full((6, before.shape[1], 3), 255, np.uint8), after]))
    print(f"wrote {out}: top = as recorded, bottom = what the pipeline sees")
