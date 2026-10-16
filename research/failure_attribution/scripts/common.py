"""Paths shared by the failure attribution scripts.

- recordings.json lists the recordings (committed); the videos are in local.config's recordings_dir (local only).
- Work files (HUD caches, series, events, thumbnails) go to research/failure_attribution/work/<recording id>/, which is
  gitignored: they are derived from the video and can be rebuilt.
- The owner's review of the detected events is committed under
  research/ground_truth/annotations/<ruleset>/genichiro/<recording id>/.
"""
import configparser
import json
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


def annotation_dir(rec: dict) -> Path:
    d = GT / "annotations" / rec.get("ruleset", "vanilla") / "genichiro" / rec["id"]
    d.mkdir(parents=True, exist_ok=True)
    return d
