"""Find Wolf's failure events in the HUD series written by hud_read.py.

Usage: python -I events.py <hud.csv> <out.csv>

Events (one row each):
    damage         HP drops by at least MIN_DROP and stays down; the onset is the first frame of the drop
    death          the death screen (the 死 kanji, death_screen.py's death_screens.csv). An HP bar reading 0 is not
                   enough: a hit can leave a sliver too thin to read, and Wolf fights on (rec 2026-10-16-castle-1:
                   0 from 224.5 s, the 死 at 240.8 s). When the 死 shows within SCREEN_AFTER of the HP reaching 0,
                   the death is that moment and is `linked` to the hit that emptied the bar (within KILL_WITHIN);
                   when it shows later, the killing hit left no mark on the bar, so the death is put SCREEN_DELAY
                   before the 死 (2.1–2.8 s on the reviewed deaths) with no link. A recording that ends with the bar
                   at 0 after a killing hit, before any 死, also ends with a death. Without death_screens.csv the HP
                   rule alone is used (0 for DEATH_HOLD right after a hit that emptied the bar). `resurrected` says
                   whether HP came back within RESURRECT_WITHIN of the death screen with the boss bar still on
                   screen; HP back without the boss bar is a respawn away from the fight
    resurrection   HP comes back after a death (not a failure; kept so the reviewer sees what happened)
    deathblow      Wolf's deathblow on the boss (not a failure): from one frame to the next, the boss HP, at least
                   BOSS_LEFT, is cleared to zero and at least BOSS_PALE of it shows as the pale just-lost segment, and
                   the HP does not come back for BOSS_HOLD (a cutscene may hide the bar). A screen fading to black also
                   empties the bar, but gradually and without the pale segment (rec 2026-10-09-castle 275.8 s). A deathblow also
                   empties Wolf's posture bar (owner, 2026-10-16: rec 2026-10-09-castle 273.6 s, the end of phase 2),
                   so no posture break is counted from DEATHBLOW_BEFORE before it to DEATHBLOW_AFTER after it. Each
                   deathblow ends a phase.
    posture_break  the owner's definition (2026-10-16): the posture bar was full or nearly full, Wolf failed to deflect
                   and was staggered, and the bar is then cleared completely; a full bar that is not cleared is not a
                   break, since a perfect deflect never breaks posture. Detected from the break frame, as the owner
                   suggested: the bar turns into the wide red break line (hud_read.py) for at least LINE_HOLD samples,
                   the posture read at least PRE_HIGH in the PRE_WINDOW before it (a full bar can read as low as 0.84
                   because its ends taper), and the bar is gone within CLEAR_WITHIN after the line and stays gone for
                   CLEAR_HOLD. Wolf's deathblow and a resurrection also clear a full bar, which only turns red
                   without drawing the line (rec 2026-10-09-castle 273.6 s, 337.7 s); both windows are still ignored
                   as a guard, while a break right before a death counts. The event time is the first frame of the
                   line.
Excluded on purpose: drops right before the HUD goes away (deathblow cutscenes, the boss's defeat, menus), where the
fading bar reads as lost HP. A drop counts only while the HUD stays on screen for HUD_AFTER after its onset, and not
when the screen fades to black: then the boss bar's brightness (boss_v) falls below FADE_RATIO of what it was, while a
hit on Wolf leaves it unchanged (0.98-1.02 on every reviewed hit; 0.00 at the fade into the phase-3 cutscene, rec
2026-10-16-castle-1 175.7 s).
"""
import csv
import sys
from pathlib import Path

import numpy as np

MIN_DROP, STEP_DOWN, SETTLE, BASELINE = 0.01, 0.004, 0.2, 0.3
HUD_AFTER, FADE_RATIO, RESURRECT_WITHIN = 0.5, 0.5, 30.0
SCREEN_AFTER, SCREEN_DELAY, NEAR_ZERO = 6.0, 2.4, 0.02
DEATH_HOLD, ZERO, KILL_WITHIN = 0.5, 0.003, 1.5
LINE_MIN, LINE_HOLD, LINE_GAP = 0.6, 2, 3       # share of line columns; samples in the line; samples of gap allowed
PRE_HIGH, PRE_WINDOW, CLEAR_WITHIN, CLEAR_HOLD = 0.6, 1.0, 1.0, 0.5
RESURRECTION_MARGIN = 2.0
BOSS_LEFT, BOSS_ZERO, BOSS_PALE, BOSS_HOLD = 0.02, 0.005, 0.8, 0.5
DEATHBLOW_BEFORE, DEATHBLOW_AFTER = 1.0, 3.0


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    col = lambda k, f=float: np.array([f(r[k]) for r in rows])
    return (col("frame", int), col("time_s"), col("hud", int).astype(bool), col("hp"), col("posture_bar", int).astype(bool),
            col("posture"), col("break_line"), col("boss_bar", int).astype(bool), col("boss_hp"), col("boss_lost"),
            col("boss_v"))


def median_filter(x, k=5):
    pad = np.pad(x, k // 2, mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(pad, k), axis=1)


def hud_holds(hud, t, i, seconds):
    end = np.searchsorted(t, t[i] + seconds)
    return bool(hud[i:end + 1].all())


def fading(t, v, i):
    """The screen fades to black around sample i: the boss bar's brightness falls below FADE_RATIO of before."""
    a, b = np.searchsorted(t, t[i] - 0.3), np.searchsorted(t, t[i] - 0.1)
    c, d = np.searchsorted(t, t[i] + 0.2), np.searchsorted(t, t[i] + 0.8)
    before, after = np.median(v[a:max(b, a + 1)]), np.median(v[c:max(d, c + 1)])
    return before > 20 and after < FADE_RATIO * before


def resurrection(t, hud, hpm, boss_bar, j):
    """Index where HP comes back after sample j with the boss bar on screen, or None."""
    k, limit = j + 1, min(len(t), int(np.searchsorted(t, t[j] + RESURRECT_WITHIN)))
    while k < limit and not (hud[k] and hpm[k] > ZERO):
        k += 1
    return k if k < limit and boss_bar[k] else None


def detect(frame, t, hud, hp, bar, po, ln, boss_bar, boss_hp, boss_lost, boss_v, screens=None):
    dt = float(np.median(np.diff(t)))
    hpm = median_filter(hp)
    events = []

    # damage
    i = 1
    while i < len(t):
        if hud[i] and hud[i - 1] and hpm[i] < hpm[i - 1] - STEP_DOWN:
            # the level before the drop: a flash or petals can push one or two samples up for a moment, and
            # falling back from them is not a hit (rec 2026-10-16-castle-1 80.6 s, -2 150.2 s, 2026-10-09-castle 213.6 s)
            start, j = i, i
            before = min(hpm[i - 1], float(np.median(hpm[max(0, i - round(BASELINE / dt)):i])))
            while j + 1 < len(t) and hud[j + 1] and hpm[j + 1] <= hpm[j] + 0.002 and t[j + 1] - t[start] < 0.6:
                j += 1
            settle = hpm[min(len(t) - 1, j + int(SETTLE / dt))]
            if before - hpm[j] >= MIN_DROP and before - settle >= MIN_DROP and hud_holds(hud, t, start, HUD_AFTER) \
                    and not fading(t, boss_v, start):
                events.append({"type": "damage", "i": start, "hp_before": before, "hp_after": hpm[j]})
            i = j + 1
        else:
            i += 1

    # deaths and resurrections
    deaths = []
    killer_of = lambda i: next((e for e in reversed(events) if e["type"] == "damage" and e["i"] <= i  # noqa: E731
                                and e["hp_after"] <= 0.05 and t[i] - t[e["i"]] <= KILL_WITHIN), None)
    zero = hud & (hpm <= ZERO)
    near = ~hud | (hpm <= NEAR_ZERO)              # walking back to where the bar emptied: noise and HUD flicker
    for a, b in (screens or []):
        i = int(np.searchsorted(t, a))
        while i > 0 and near[i - 1]:
            i -= 1
        if t[min(i, len(t) - 1)] <= a and a - t[i] <= SCREEN_AFTER:
            killer, note = killer_of(i), ""
        else:
            i, killer = int(np.searchsorted(t, a - SCREEN_DELAY)), None
            note = "the killing hit left no mark on the HP bar (it read 0 already)"
        k = resurrection(t, hud, hpm, boss_bar, int(np.searchsorted(t, b)))
        events.append({"type": "death", "i": i, "hp_before": killer["hp_before"] if killer else 0.0, "hp_after": 0.0,
                       "resurrected": k is not None, "linked": killer, "why": note})
        deaths.append((t[i], t[k] if k is not None else b))
        if k is not None:
            events.append({"type": "resurrection", "i": k, "hp_before": 0.0, "hp_after": hpm[min(len(t) - 1, k + 2)]})
    if screens is not None:
        z = np.flatnonzero(zero)
        last_seen = max((d[1] for d in deaths), default=-1.0)
        if len(z) and t[-1] - t[z[-1]] <= 1.0 and t[z[-1]] > last_seen:
            i = z[-1]
            while i > 0 and near[i - 1]:
                i -= 1
            killer = killer_of(i)
            if killer and t[-1] - t[i] >= DEATH_HOLD:
                events.append({"type": "death", "i": i, "hp_before": killer["hp_before"], "hp_after": 0.0,
                               "resurrected": False, "linked": killer, "why": "the recording ends before the death screen"})
                deaths.append((t[i], t[-1]))
    i = 0 if screens is None else len(t)
    while i < len(t):
        if hud[i] and hpm[i] <= ZERO and hud_holds(hud, t, i, DEATH_HOLD) and (hpm[i:np.searchsorted(t, t[i] + DEATH_HOLD) + 1] <= ZERO).all():
            j = i
            while j + 1 < len(t) and hpm[j + 1] <= ZERO and hud[j + 1]:
                j += 1
            k, limit = j + 1, min(len(t), int(np.searchsorted(t, t[j] + RESURRECT_WITHIN)))
            while k < limit and not (hud[k] and hpm[k] > ZERO):
                k += 1
            back = k < limit and bool(boss_bar[k])
            killer = next((e for e in reversed(events) if e["type"] == "damage" and e["i"] <= i and e["hp_after"] <= 0.05
                           and t[i] - t[e["i"]] <= KILL_WITHIN), None)
            if killer is None:
                i = j + 1
                continue
            d = {"type": "death", "i": i, "hp_before": killer["hp_before"] if killer else 0.0, "hp_after": 0.0,
                 "resurrected": back, "linked": killer}
            events.append(d)
            deaths.append((t[i], t[k] if back else t[j]))
            if back:
                events.append({"type": "resurrection", "i": k, "hp_before": 0.0, "hp_after": hpm[min(len(t) - 1, k + 2)]})
            i = j + 1
        else:
            i += 1

    # Wolf's deathblows: the boss HP bar cleared
    blows = []
    for i in range(1, len(t)):
        left = boss_hp[i - 1]
        if not (boss_bar[i - 1] and boss_bar[i] and left >= BOSS_LEFT and boss_hp[i] <= BOSS_ZERO
                and boss_lost[i] >= BOSS_PALE * left):
            continue
        hold = (t > t[i]) & (t <= t[i] + BOSS_HOLD) & boss_bar
        if not (boss_hp[hold] > BOSS_ZERO).any():
            blows.append(t[i])
            events.append({"type": "deathblow", "i": i, "hp_before": hpm[i], "hp_after": hpm[i], "boss_before": left})

    # posture breaks
    line = hud & (ln >= LINE_MIN)
    i = 0
    while i < len(t):
        if not line[i]:
            i += 1
            continue
        j, k = i, i + 1
        while k < len(t) and k - j <= LINE_GAP:
            if line[k]:
                j = k
            k += 1
        before = (t >= t[i] - PRE_WINDOW) & (t < t[i])
        high = po[before].max() if before.any() else 0.0
        gone = None
        for m in range(i, min(len(t), np.searchsorted(t, t[j] + CLEAR_WITHIN) + 1)):
            if not bar[m]:
                end = m
                while end + 1 < len(t) and not bar[end + 1]:
                    end += 1
                if t[end] - t[m] >= CLEAR_HOLD:
                    gone = m
                    break
        near_death = any(a <= t[i] <= b + RESURRECTION_MARGIN for a, b in deaths)
        near_blow = any(d - DEATHBLOW_BEFORE <= t[i] <= d + DEATHBLOW_AFTER for d in blows)
        if line[i:j + 1].sum() >= LINE_HOLD and high >= PRE_HIGH and gone is not None and not near_death and not near_blow:
            events.append({"type": "posture_break", "i": i, "hp_before": hpm[i], "hp_after": hpm[gone],
                           "line_end": t[j], "high": high, "cleared": t[gone]})
        i = j + 1

    events.sort(key=lambda e: (e["i"], e["type"] != "damage"))
    return events


def main():
    frame, t, hud, hp, bar, po, ln, boss_bar, boss_hp, boss_lost, boss_v = load(sys.argv[1])
    path = Path(sys.argv[1]).parent / "death_screens.csv"
    screens = [(float(r["start_s"]), float(r["end_s"])) for r in csv.DictReader(open(path, encoding="utf-8"))] \
        if path.exists() else None
    events = detect(frame, t, hud, hp, bar, po, ln, boss_bar, boss_hp, boss_lost, boss_v, screens)
    with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["key", "type", "time_s", "frame", "hp_before", "hp_after", "linked", "note"])
        for e in events:
            key = f"{e['type']}@{t[e['i']]:.1f}"
            linked = f"damage@{t[e['linked']['i']]:.1f}" if e.get("linked") else ""
            note = ""
            if e["type"] == "death":
                note = "resurrected" if e["resurrected"] else "not resurrected (no HP back with the boss bar on screen)"
                if e.get("why"):
                    note += f"; {e['why']}"
            elif e["type"] == "deathblow":
                note = f"boss HP {e['boss_before']:.2f} -> 0"
            elif e["type"] == "posture_break":
                note = f"break line to {e['line_end']:.2f}s, posture before {e['high']:.2f}, bar cleared at {e['cleared']:.2f}s"
            w.writerow([key, e["type"], f"{t[e['i']]:.3f}", int(frame[e["i"]]), f"{e['hp_before']:.3f}", f"{e['hp_after']:.3f}", linked, note])
    counts = {k: sum(1 for e in events if e["type"] == k) for k in ("damage", "death", "resurrection", "posture_break", "deathblow")}
    print(f"wrote {sys.argv[2]}: {counts}")


if __name__ == "__main__":
    main()
