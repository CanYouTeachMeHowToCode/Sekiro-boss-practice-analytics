"""Find Wolf's failure events in the HUD series written by hud_read.py.

Usage: python -I events.py <hud.csv> <out.csv>

Events (one row each):
    damage         HP drops by at least MIN_DROP and stays down; the onset is the first frame of the drop
    death          HP reaches 0 and stays there for DEATH_HOLD while the HUD is on screen, right after a damage event
                   that emptied the bar (`linked`); a bar that goes dark without a hit (a deathblow cutscene fading
                   the HUD) is not a death. `resurrected` says whether HP came back before the HUD went away
    resurrection   HP comes back after a death (not a failure; kept so the reviewer sees what happened)
    posture_break  the owner's definition (2026-10-16): the posture bar was full or nearly full (>= POSTURE_HIGH for
                   at least POSTURE_HOLD) and is then cleared completely (bar gone within CLEAR_WITHIN and staying gone
                   for CLEAR_HOLD). A full bar that is not cleared is not a break, since a perfect deflect never breaks
                   posture. A clear from a death to just after its resurrection is not a break (the bar stays
                   until the resurrection, then empties); a break right before a death still counts. The event
                   time is the last nearly full sample before the clear, close to the hit that broke the posture.
Excluded on purpose: drops right before the HUD goes away (deathblow cutscenes, the boss's defeat, menus), where the
fading bar reads as lost HP. A drop counts only while the HUD stays on screen for HUD_AFTER after its onset.
"""
import csv
import sys

import numpy as np

MIN_DROP, STEP_DOWN, SETTLE = 0.01, 0.004, 0.2
HUD_AFTER = 0.5
DEATH_HOLD, ZERO, KILL_WITHIN = 0.5, 0.003, 1.5
POSTURE_HIGH, POSTURE_HOLD, CLEAR_WITHIN, CLEAR_HOLD = 0.85, 0.1, 1.0, 0.5
RESURRECTION_MARGIN = 2.0


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    col = lambda k, f=float: np.array([f(r[k]) for r in rows])
    return col("frame", int), col("time_s"), col("hud", int).astype(bool), col("hp"), col("posture_bar", int).astype(bool), col("posture")


def median_filter(x, k=5):
    pad = np.pad(x, k // 2, mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(pad, k), axis=1)


def hud_holds(hud, t, i, seconds):
    end = np.searchsorted(t, t[i] + seconds)
    return bool(hud[i:end + 1].all())


def detect(frame, t, hud, hp, bar, po):
    dt = float(np.median(np.diff(t)))
    hpm = median_filter(hp)
    events = []

    # damage
    i = 1
    while i < len(t):
        if hud[i] and hud[i - 1] and hpm[i] < hpm[i - 1] - STEP_DOWN:
            start, before, j = i, hpm[i - 1], i
            while j + 1 < len(t) and hud[j + 1] and hpm[j + 1] <= hpm[j] + 0.002 and t[j + 1] - t[start] < 0.6:
                j += 1
            settle = hpm[min(len(t) - 1, j + int(SETTLE / dt))]
            if before - hpm[j] >= MIN_DROP and before - settle >= MIN_DROP and hud_holds(hud, t, start, HUD_AFTER):
                events.append({"type": "damage", "i": start, "hp_before": before, "hp_after": hpm[j]})
            i = j + 1
        else:
            i += 1

    # deaths and resurrections
    deaths = []
    i = 0
    while i < len(t):
        if hud[i] and hpm[i] <= ZERO and hud_holds(hud, t, i, DEATH_HOLD) and (hpm[i:np.searchsorted(t, t[i] + DEATH_HOLD) + 1] <= ZERO).all():
            j = i
            while j + 1 < len(t) and hpm[j + 1] <= ZERO and hud[j + 1]:
                j += 1
            back = j + 1 < len(t) and hud[j + 1] and hpm[j + 1] > ZERO
            killer = next((e for e in reversed(events) if e["type"] == "damage" and e["i"] <= i and e["hp_after"] <= 0.05
                           and t[i] - t[e["i"]] <= KILL_WITHIN), None)
            if killer is None:
                i = j + 1
                continue
            d = {"type": "death", "i": i, "hp_before": killer["hp_before"] if killer else 0.0, "hp_after": 0.0,
                 "resurrected": back, "linked": killer}
            events.append(d)
            deaths.append((t[i], t[j + 1] if back else t[j]))
            if back:
                events.append({"type": "resurrection", "i": j + 1, "hp_before": 0.0, "hp_after": hpm[min(len(t) - 1, j + 3)]})
            i = j + 1
        else:
            i += 1

    # posture breaks
    i = 0
    while i < len(t):
        if po[i] >= POSTURE_HIGH:
            j = i
            while j + 1 < len(t) and po[j + 1] >= POSTURE_HIGH:
                j += 1
            if t[j] - t[i] + dt >= POSTURE_HOLD:
                window = range(j + 1, min(len(t), np.searchsorted(t, t[j] + CLEAR_WITHIN) + 1))
                gone = next((m for m in window if not bar[m] and hud[m]), None)
                if gone is not None:
                    end = gone
                    while end + 1 < len(t) and not bar[end + 1]:
                        end += 1
                    near_death = any(a <= t[gone] <= b + RESURRECTION_MARGIN for a, b in deaths)
                    if t[end] - t[gone] >= CLEAR_HOLD and not near_death:
                        events.append({"type": "posture_break", "i": j, "hp_before": hpm[i], "hp_after": hpm[gone],
                                       "cleared": t[gone]})
            i = j + 1
        else:
            i += 1

    events.sort(key=lambda e: (e["i"], e["type"] != "damage"))
    return events


def main():
    frame, t, hud, hp, bar, po = load(sys.argv[1])
    events = detect(frame, t, hud, hp, bar, po)
    with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["key", "type", "time_s", "frame", "hp_before", "hp_after", "linked", "note"])
        for e in events:
            key = f"{e['type']}@{t[e['i']]:.1f}"
            linked = f"damage@{t[e['linked']['i']]:.1f}" if e.get("linked") else ""
            note = ""
            if e["type"] == "death":
                note = "resurrected" if e["resurrected"] else "not resurrected before the HUD went away"
            elif e["type"] == "posture_break":
                note = f"bar cleared at {e['cleared']:.2f}s"
            w.writerow([key, e["type"], f"{t[e['i']]:.3f}", int(frame[e["i"]]), f"{e['hp_before']:.3f}", f"{e['hp_after']:.3f}", linked, note])
    counts = {k: sum(1 for e in events if e["type"] == k) for k in ("damage", "death", "resurrection", "posture_break")}
    print(f"wrote {sys.argv[2]}: {counts}")


if __name__ == "__main__":
    main()
