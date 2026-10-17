"""Paths shared by the failure attribution scripts.

- recordings.json lists the recordings (committed); the videos are in local.config's recordings_dir (local only).
- Work files (HUD caches, series, events, thumbnails) go to research/failure_attribution/work/<recording id>/, which is
  gitignored: they are derived from the video and can be rebuilt.
- The owner's review of the detected events is committed under
  research/ground_truth/annotations/<ruleset>/genichiro/<recording id>/.
- While hud_pipeline.py runs, work/<recording id>/progress.json says which step it is on and how far that step is
  (report()); progress() turns it into an overall fraction and a time left, for the review page's /progress view.
"""
import configparser
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FA = HERE.parent
REPO = FA.parent.parent
GT = REPO / "research/ground_truth"
WORK = FA / "work"


def recordings() -> dict:
    data = json.loads((FA / "recordings.json").read_text(encoding="utf-8"))
    return {r["id"]: r for r in data["recordings"]}


def video_path(rec: dict) -> Path:
    config = configparser.ConfigParser()
    config.read(GT / "local.config", encoding="utf-8")
    path = Path(config["paths"]["recordings_dir"]) / rec["file_name"]
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: put the recording in recordings_dir (local.config)")
    return path


def work_dir(rec_id: str) -> Path:
    d = WORK / rec_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# the steps of hud_pipeline.py, in order: id, name shown, share of the run time
STEPS = [("hud_cache", "读 HUD", 0.40), ("events", "找失败事件", 0.02), ("boss_track", "跟踪 Boss", 0.45),
         ("features", "提取特征", 0.04), ("moves", "认招式", 0.03), ("thumbs", "缩略图", 0.06)]


def report(work: Path, stage: str, fraction: float = 0.0, start: bool = False):
    path = work / "progress.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not start else {}
    if start:
        data["started"] = time.time()
    data.update(stage=stage, fraction=round(min(max(fraction, 0.0), 1.0), 4), updated=time.time())
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def progress(work: Path):
    """(overall fraction, step name, step fraction, seconds used, seconds left or None, finished) or None."""
    path = work / "progress.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    if d["stage"] == "done":
        return 1.0, "完成", 1.0, d["updated"] - d.get("started", d["updated"]), 0.0, True
    used = time.time() - d.get("started", d["updated"])
    i = [s[0] for s in STEPS].index(d["stage"])
    overall = sum(s[2] for s in STEPS[:i]) + STEPS[i][2] * d["fraction"]
    left = used * (1 - overall) / overall if overall > 0.03 else None
    return overall, STEPS[i][1], d["fraction"], used, left, False


def observation_dir(rec: dict):
    """The V3.1 overlay readings of a dev-menu recording (frames.csv, occurrences.csv), or None before they exist."""
    d = GT / "observations" / rec.get("ruleset", "vanilla") / "genichiro" / rec["id"]
    return d if rec.get("overlay") and (d / "occurrences.csv").exists() else None


def annotation_dir(rec: dict) -> Path:
    d = GT / "annotations" / rec.get("ruleset", "vanilla") / "genichiro" / rec["id"]
    d.mkdir(parents=True, exist_ok=True)
    return d
