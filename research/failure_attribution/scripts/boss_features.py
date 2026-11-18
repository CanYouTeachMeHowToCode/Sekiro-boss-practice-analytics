"""DINOv2 features of the boss crops of a registered recording, on the GPU (analysis/sekiro_analysis/boss_features.py).

Usage: python -I boss_features.py <recording id | all> [--model vit_small_patch14_dinov2.lvd142m]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import recordings, work_dir  # noqa: E402
from sekiro_analysis.boss_features import MODEL, features, short  # noqa: E402,F401


def main():
    name = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else MODEL
    recs = recordings()
    for rec_id in (list(recs) if sys.argv[1] == "all" else [sys.argv[1]]):
        features(work_dir(rec_id), name, device="cuda")


if __name__ == "__main__":
    main()
