"""The fight's phase read from the HUD (version 4, owner, 2026-11-20).

Version 3 and before counted the deathblows (events.py: the boss HP bar clearing, its "just lost" part pale over at
least BOSS_PALE of what was left) and took the phase as 1 plus those since the last lost fight. One missed deathblow
put every later failure in the wrong phase, and so its move among the wrong phase's moves: in a tester's recording
about 17% darker than the owner's (recording 2 on the test server, 2026-11-20) the pale part's texture fell below the
pale threshold, none of the three deathblows counted, and every failure was phase 1.

The HUD says the phase directly (the owner's idea, 2026-11-20). Above the boss HP bar, castle Genichiro has two
deathblow dots in phase 1, the second one grey after the first deathblow (phase 2), and one dot in phase 3, where the
name under the bar becomes 巴流 苇名弦一郎 (Genichiro, Way of Tomoe). So:
- the name, matched against the upload check's templates (content_check, one per interface and phase group), tells
  phase 3 from phases 1-2;
- the second dot, lit (saturated, bright red) or not, tells phase 1 from phase 2.
A lit dot is far brighter and more saturated than anything the darker recording lost, so brightness does not move it.

A Reader is handed the frames hud_read.cache() reads anyway, so the worker does not decode the video twice, and keeps
RATE of them a second; scan() decodes a video for it on its own (research, where the HUD cache is usually there
already). Both keep the same frames: RATE a second is a multiple of hud_read's step at 30 and 60 fps. hud_phase.csv
holds, per sample, how much of each dot's core is lit red and the best name template with its score.

phase_at() gives the phase just before a moment from the last samples with the boss's dots on screen. Where the HUD says
nothing (no such sample within LOOKBACK_S, or no name read, as under the dev-menu overlay, which covers the name) it
falls back to the deathblow count, as before.
"""
import csv
from pathlib import Path

import cv2
import numpy as np

from . import sampling
from .content_check import name_score, prepare

RATE = 5                                  # samples a second
DOTS = ((175, 93), (227, 93))             # centres of the deathblow dots at 2560×1440
DOT_R = 8                                 # radius of the core read
LIT_FRACTION = 0.35                       # share of the core that must be lit red
NAME_MIN = 0.6                            # a name template's score that says which name it is
LAST = 5                                  # samples that decide (one second)
LOOKBACK_S = 30.0                         # how far back samples may be
FIELDS = ["time_s", "dot1", "dot2", "name", "name_score"]


def lit(frame, centre):
    """Share of the dot's core (radius DOT_R around `centre`, a 2560×1440 frame) that is lit: red to orange, saturated
    and bright, as a deathblow dot glows."""
    x, y = centre
    core = cv2.cvtColor(frame[y - DOT_R:y + DOT_R + 1, x - DOT_R:x + DOT_R + 1], cv2.COLOR_BGR2HSV).astype(int)
    yy, xx = np.mgrid[-DOT_R:DOT_R + 1, -DOT_R:DOT_R + 1]
    disc = xx ** 2 + yy ** 2 <= DOT_R ** 2
    h, s, v = core[..., 0][disc], core[..., 1][disc], core[..., 2][disc]
    return float((((h <= 20) | (h >= 165)) & (s >= 90) & (v >= 180)).mean())


class Reader:
    """Called with (frame number, decoded unmasked frame) for frames of a video at `fps`; reads RATE of them a second,
    and write() saves hud_phase.csv. `templates` from content_check.load_templates; `overlay`: a dev-menu recording,
    whose overlay covers the name, so only the dots are read."""

    def __init__(self, templates, fps, overlay=False):
        self.templates, self.fps, self.overlay = templates, fps, overlay
        self.every = sampling.every(fps, RATE)
        self.rows = []

    def __call__(self, n, frame):
        if n % self.every or frame is None:
            return
        f = prepare(frame)
        score, key = (None, None) if self.overlay else name_score(f, self.templates)
        self.rows.append([f"{n / self.fps:.3f}", f"{lit(f, DOTS[0]):.3f}", f"{lit(f, DOTS[1]):.3f}",
                          key.split("|")[1] if key else "", f"{score:.3f}" if score is not None else ""])

    def write(self, work):
        with open(Path(work) / "hud_phase.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(FIELDS)
            w.writerows(self.rows)


def scan(video, work, templates, overlay=False):
    """Writes work/hud_phase.csv, decoding the video on its own; the same as hud_read.cache(..., frames=Reader)."""
    cap = cv2.VideoCapture(str(video))
    reader = Reader(templates, cap.get(cv2.CAP_PROP_FPS), overlay)
    n = 0
    while cap.grab():
        if n % reader.every == 0:
            ok, f = cap.retrieve()
            reader(n, f if ok else None)
        n += 1
    reader.write(work)


def load(work):
    """hud_phase.csv of `work` as arrays: time, the two dots' lit shares, and the name group where a template scored at
    least NAME_MIN ("" elsewhere); None without the file."""
    path = Path(work) / "hud_phase.csv"
    if not path.exists():
        return None
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return {"t": np.array([float(r["time_s"]) for r in rows]),
            "dot1": np.array([float(r["dot1"]) for r in rows]),
            "dot2": np.array([float(r["dot2"]) for r in rows]),
            "name": np.array([r["name"] if r["name_score"] and float(r["name_score"]) >= NAME_MIN else ""
                              for r in rows])}


def phase_at(t, hud, counted):
    """The phase just before `t` from the HUD (`hud` from load()), or `counted` (the deathblow count, moves.phase_at)
    where the HUD does not say. The last LAST samples with the first dot lit (the boss's HUD on screen) within
    LOOKBACK_S decide by majority: the name for phase 3, then the second dot for 1 or 2."""
    if hud is None:
        return counted
    seen = np.nonzero((hud["t"] < t) & (hud["t"] >= t - LOOKBACK_S) & (hud["dot1"] >= LIT_FRACTION))[0][-LAST:]
    if len(seen) == 0:
        return counted
    named = [n for n in hud["name"][seen] if n]
    if named and sum(n == "3" for n in named) * 2 > len(named):
        return 3
    if sum(hud["dot2"][seen] >= LIT_FRACTION) * 2 > len(seen):
        return 1
    if named:
        return 2
    return min(3, max(2, counted))        # no name read (dev-menu overlay): 2 or 3 by the deathblows
