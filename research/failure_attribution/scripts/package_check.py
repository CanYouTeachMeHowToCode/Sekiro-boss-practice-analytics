"""Checks of the analysis package against the research pipeline (V4 M3, 2026-11-17).

Usage:
    python -I package_check.py same <work dir A> <work dir B>
        every output two runs of the pipeline wrote (HUD cache and series, death screens, events, reversals, boss track,
        crops, features, predictions, thumbnails): identical, array by array and byte by byte
    python -I package_check.py cpu <data folder> <recording id | all-test>...
        the features computed on the CPU (fp32) instead of the GPU (fp16, how every research result was made), from the
        recording's boss crops, then its failures predicted with the worker's references: what changes

The moving of the steps into the package must leave every output as it was (the freeze rule): `same` compares a run
of the code from before the move (a git worktree pinned at bd3ce15) with a run of the code after it, from the video.
"""
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import recordings, work_dir  # noqa: E402
from sekiro_analysis import moves as mm  # noqa: E402
from sekiro_analysis import references as saved  # noqa: E402
from sekiro_analysis.boss_features import MODEL, features  # noqa: E402
from sekiro_analysis.pipeline import Data  # noqa: E402

SKIP = {"progress.json"}


def same(a, b):
    a, b = Path(a), Path(b)
    names = sorted({p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()}
                   | {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()})
    bad = 0
    for name in names:
        if name in SKIP:
            continue
        pa, pb = a / name, b / name
        if not pa.exists() or not pb.exists():
            print(f"  {name}: only in {'B' if not pa.exists() else 'A'}")
            bad += 1
            continue
        if name.endswith(".npz"):
            da, db = np.load(pa), np.load(pb)
            diff = [k for k in sorted(set(da.files) | set(db.files))
                    if k not in da.files or k not in db.files or not np.array_equal(da[k], db[k])]
            ok = not diff
            what = "arrays equal" if ok else f"arrays differ: {diff}"
        elif name.endswith(".npy"):
            ok = np.array_equal(np.load(pa), np.load(pb))
            what = "array equal" if ok else "array differs"
        else:
            ok = pa.read_bytes() == pb.read_bytes()
            what = "same bytes" if ok else "bytes differ"
        bad += not ok
        if not ok or not name.startswith("thumbs/"):
            print(f"  {name}: {what}")
    thumbs = sum(1 for n in names if n.startswith("thumbs/"))
    print(f"{a.name} vs {b.name}: {len(names) - len(SKIP & set(names))} files ({thumbs} thumbnails), "
          f"{bad} different")
    return bad == 0


def cpu(folder, ids):
    refs, gaps, moves, st = saved.load(folder)
    weights = Data(folder).weights
    recs = recordings()
    if ids == ["all-test"]:
        ids = [i for i, r in recs.items() if r.get("set") in ("test", "scenario")
               and (work_dir(i) / "boss_crops.npz").exists()]
    total = changed_answer = changed_sure = 0
    largest = 0.0
    for rec_id in ids:
        src = work_dir(rec_id)
        with tempfile.TemporaryDirectory(prefix="cpu-") as tmp:
            tmp = Path(tmp)
            for name in ("boss_crops.npz", "boss_track.csv", "events.csv"):
                shutil.copyfile(src / name, tmp / name)
            features(tmp, MODEL, "cpu", weights=weights)
            gpu_f = np.load(src / "boss_feats_small14.npy").astype(np.float32)
            cpu_f = np.load(tmp / "boss_feats_small14.npy").astype(np.float32)
            d = gpu_f.shape[1] // 2
            cos = (gpu_f[:, :d] * cpu_f[:, :d]).sum(1)
            q = mm.Rec(tmp, st["model"], st["part"], st["trend"])
            rows = mm.predict_rows(q, mm.read(tmp / "events.csv"), refs, gaps, moves, st)
        gpu_rows = mm.read(src / "failure_predictions.csv")
        by_key = {r["key"]: r for r in gpu_rows}
        notes = []
        for r in rows:
            g = by_key.get(r["key"])
            if g is None:
                notes.append(f"{r['key']} only on the CPU")
                continue
            total += 1
            cs = {c.rsplit(':', 1)[0]: float(c.rsplit(':', 1)[1]) for c in r["candidates"].split()}
            gs = {c.rsplit(':', 1)[0]: float(c.rsplit(':', 1)[1]) for c in g["candidates"].split()}
            largest = max([largest] + [abs(cs[m] - gs[m]) for m in cs if m in gs])
            if r["move"] != g["move"]:
                changed_answer += 1
                notes.append(f"{r['key']} first candidate {g['move']} -> {r['move']}")
            if r["certain"] != g["certain"]:
                changed_sure += 1
                notes.append(f"{r['key']} sure {g['certain']} -> {r['certain']} (confidence {g['confidence']} -> "
                             f"{r['confidence']})")
        if len(rows) != len(gpu_rows) or [r["events"] for r in rows] != [g["events"] for g in gpu_rows]:
            notes.append(f"failures differ: GPU {len(gpu_rows)}, CPU {len(rows)}")
        print(f"{rec_id}: CLS cosine CPU vs GPU min {cos.min():.5f}, mean {cos.mean():.6f}; {len(rows)} failures"
              + ("; " + "; ".join(notes) if notes else "; same answers and sureness"), flush=True)
    print(f"{total} failures: first candidate changed {changed_answer}, sure changed {changed_sure}, "
          f"largest score change {largest:.3f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "same":
        sys.exit(0 if same(sys.argv[2], sys.argv[3]) else 1)
    elif sys.argv[1] == "cpu":
        cpu(sys.argv[2], sys.argv[3:])
