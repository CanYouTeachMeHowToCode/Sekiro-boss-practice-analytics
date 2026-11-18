"""The references of the move recognition, saved for the recording worker.

The research work folder holds what the references are made of (the dev-menu recordings' boss features and overlay
readings, the owner's labelled hits); the research script research/failure_attribution/scripts/export_analysis_data.py
builds them the way move_match.py predict does and saves them here, in the worker's data folder: references.npz (each
reference recording's crop times, crops with a lock-on dot, detrended features) and references.json (each reference
hit, the merge windows, the product moves and the settings). Loading them gives predict_rows() exactly the references
the research prediction uses, in the same order.
"""
import json
from pathlib import Path

import numpy as np

from .moves import Rec

NPZ, JSON = "references.npz", "references.json"


def _plain(o):
    return o.item() if hasattr(o, "item") else str(o)


def save(folder, refs, gaps, moves, settings, about=""):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    recs, index = [], {}
    for ref in refs:
        if id(ref["rec"]) not in index:
            index[id(ref["rec"])] = len(recs)
            recs.append(ref["rec"])
    arrays = {}
    for i, r in enumerate(recs):
        arrays[f"t{i}"], arrays[f"ok{i}"], arrays[f"f{i}"] = r.t, r.ok, r.f
    np.savez(folder / NPZ, **arrays)
    meta = {"about": about, "settings": settings, "gaps": gaps,
            "moves": [{"slug": m["slug"], "zh": m["zh"], "en": m["en"], "phases": sorted(m["phases"])} for m in moves],
            "refs": [{"rec": index[id(ref["rec"])], "anim": ref["anim"], "hit": ref["hit"], "kind": ref["kind"],
                      "t": ref["t"], "phase": ref["phase"], "moves": ref["moves"]} for ref in refs]}
    (folder / JSON).write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=_plain), encoding="utf-8")


def load(folder):
    """(refs, gaps, moves, settings) for moves.predict_rows()."""
    folder = Path(folder)
    meta = json.loads((folder / JSON).read_text(encoding="utf-8"))
    d = np.load(folder / NPZ)
    count = 1 + max(r["rec"] for r in meta["refs"])
    recs = [Rec.from_arrays(d[f"t{i}"], d[f"ok{i}"], d[f"f{i}"]) for i in range(count)]
    refs = [{**r, "rec": recs[r["rec"]]} for r in meta["refs"]]
    moves = [{**m, "phases": set(m["phases"])} for m in meta["moves"]]
    return refs, meta["gaps"], moves, meta["settings"]
