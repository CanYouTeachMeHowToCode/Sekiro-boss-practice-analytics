"""Contact sheets: for every run, the overlay line at the run's middle frame next to the script's read."""
import csv, sys, cv2, numpy as np
from pathlib import Path
video, data, out_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
runs = list(csv.DictReader(open(data / "runs.csv", encoding="utf-8")))
want = {}
for r in runs:
    mid = (int(r["start_frame"]) + int(r["end_frame"])) // 2
    want.setdefault(mid, []).append(r)
cap = cv2.VideoCapture(video)
crops = {}
i = 0
last = max(want)
while i <= last:
    ok, f = cap.read()
    if not ok: break
    if i in want:
        crops[i] = f[150:180, 125:525].copy()
    i += 1
rows = []
for r in runs:
    mid = (int(r["start_frame"]) + int(r["end_frame"])) // 2
    label = np.zeros((30, 330, 3), np.uint8)
    color = (0, 200, 255) if r["flags"] else (0, 255, 0)
    cv2.putText(label, f"#{r['run']:>3} {float(r['start_time']):6.2f}s {r['anim'][5:]} {r['char'][3:5]} {r['flags'][:12]}",
                (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    rows.append(np.hstack([label, crops[mid]]))
per = 40
for s in range(0, len(rows), per):
    sheet = np.vstack(rows[s:s + per])
    cv2.imwrite(str(out_dir / f"sheet_{s // per + 1:02d}.png"), sheet)
print("sheets:", (len(rows) + per - 1) // per)
