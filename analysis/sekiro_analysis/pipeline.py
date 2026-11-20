"""One video through the whole pipeline: what the recording worker calls.

check() is the upload check (is it a castle Genichiro fight?); analyze() finds the failures and their moves, running
the steps of research/failure_attribution/scripts/hud_pipeline.py in the same order with the same code: the HUD read,
the death screen, the failure events, the lightning reversals, the boss track, the boss features and the move
recognition. Intermediate files go to a work folder, as in research.

Everything taken from the game's images (the 死 mask, the 打雷 glyph, the boss-name templates, the castle-roof scene
features) and the move references are read from a local data folder (Data), never from the repository: the research
script research/failure_attribution/scripts/export_analysis_data.py writes it.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import boss_features, boss_track, content_check, death_screen, events, hud_read, moves, references, reversal

# version 3 (2026-11-18): the steps read 30 samples a second at any frame rate (sampling.py); at 60 fps the outputs are
# version 2's, byte for byte
VERSION = "v3"
# share of the run time of each step, as measured in research (common.STEPS, without the review thumbnails)
STEPS = [("hud_cache", 0.40), ("events", 0.02), ("reversal", 0.04), ("boss_track", 0.41), ("features", 0.04),
         ("moves", 0.03)]
WEIGHTS = "dinov2_small14.safetensors"


class Data:
    """The local data folder."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.death_mask = self.folder / "death_mask.npy"
        self.glyph = self.folder / "glyph_dalei.npy"
        self.name_templates = self.folder / "name_templates.npz"
        self.scene_refs = self.folder / "scene_refs.npz"
        self.weights = self.folder / WEIGHTS

    def missing(self):
        """The files the pipeline needs that the folder does not have."""
        need = [self.death_mask, self.glyph, self.name_templates, self.scene_refs, self.weights,
                self.folder / references.NPZ, self.folder / references.JSON]
        return [p.name for p in need if not p.exists()]


@dataclass(frozen=True)
class Failure:
    time_s: float
    type: str                                       # damage, posture_break or death
    phase: int
    sure: bool
    move: str | None                                # the move's slug when sure
    candidates: tuple[tuple[str, float], ...]       # (slug, score), best first
    events: tuple[tuple[str, float], ...]           # (type, time_s) of the events merged into this failure


def default_device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def check(video, data, device=None):
    """(reject code or None, the scores) of the upload check."""
    scene = content_check.Scene(device or default_device(), data.weights)
    res = content_check.check(video, scene, content_check.load_templates(data.name_templates), data.scene_refs)
    return content_check.verdict(res), res


def analyze(video, work, data, device=None, progress=None):
    """The failures of one fight, in time order. `work` is a folder for the intermediate files; `progress` (optional)
    is called with the fraction done."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    device = device or default_device()
    total = sum(w for _, w in STEPS)

    def stage(i):
        done = sum(w for _, w in STEPS[:i])
        return (lambda f: progress((done + STEPS[i][1] * f) / total)) if progress else None

    hud_read.cache(video, work / "hud_cache.npz", None, stage(0))           # 30 samples a second (sampling.step)
    hud_read.series(work / "hud_cache.npz", work / "hud.csv")
    death_screen.scan(video, work, np.load(data.death_mask))
    events.write_events(work / "hud.csv", work / "events.csv")
    reversal.apply(video, work, reversal.Glyph(np.load(data.glyph)))     # a lightning reversal is not a failure
    boss_track.track(video, work, None, stage(3))
    boss_features.features(work, boss_features.MODEL, device, weights=data.weights if data.weights.exists() else None,
                           progress=stage(4))
    refs, gaps, move_list, st = references.load(data.folder)
    q = moves.Rec(work, st["model"], st["part"], st["trend"])
    evs = moves.read(work / "events.csv")
    rows = moves.predict_rows(q, evs, refs, gaps, move_list, st)
    moves.write_rows(rows, work / "failure_predictions.csv")
    if progress:
        progress(1.0)
    when = {e["key"]: float(e["time_s"]) for e in moves.read(work / "events.csv")}
    out = []
    for r in rows:
        sure = r["certain"] == "1"
        out.append(Failure(
            time_s=float(r["time_s"]), type=r["type"], phase=int(r["phase"]), sure=sure,
            move=r["move"] if sure else None,
            candidates=tuple((c.rsplit(":", 1)[0], float(c.rsplit(":", 1)[1])) for c in r["candidates"].split()),
            events=tuple((k.split("@")[0], when.get(k, float(k.split("@")[1]))) for k in r["events"].split())))
    return out
