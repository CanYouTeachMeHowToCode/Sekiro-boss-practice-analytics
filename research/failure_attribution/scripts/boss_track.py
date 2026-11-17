"""Track the boss through a registered recording (the tracking: analysis/sekiro_analysis/boss_track.py).

Usage: python -I boss_track.py <recording id | all> [--step N]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import recordings, report, video_path, work_dir  # noqa: E402
from sekiro_analysis import boss_track as bt  # noqa: E402
from sekiro_analysis.boss_track import CENTRE, CROP, DROP, HOLD, OUT, crop  # noqa: E402,F401


def track(rec_id, rec, step):
    work = work_dir(rec_id)
    bt.track(video_path(rec), work, step, progress=lambda f: report(work, "boss_track", f))


def load_crops(rec_id):
    return bt.load_crops(work_dir(rec_id))


def main():
    recs = recordings()
    step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 2
    ids = list(recs) if sys.argv[1] == "all" else [sys.argv[1]]
    for rec_id in ids:
        track(rec_id, recs[rec_id], step)


if __name__ == "__main__":
    main()
