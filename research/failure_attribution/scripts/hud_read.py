"""Read Wolf's HP and posture from the game HUD (the reading itself: analysis/sekiro_analysis/hud_read.py).

Usage:
    python -I hud_read.py cache  <video> <cache.npz> [--step N]   decode once, keep per-column HUD colours
    python -I hud_read.py series <cache.npz> <out.csv>             HP, posture and HUD visibility per frame
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import report  # noqa: E402
from sekiro_analysis.hud_read import *  # noqa: E402,F401,F403  (the research scripts import its names from here)
from sekiro_analysis.hud_read import cache, series  # noqa: E402

if __name__ == "__main__":
    if sys.argv[1] == "cache":
        step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 2
        out = Path(sys.argv[3])
        cache(sys.argv[2], out, step, progress=lambda f: report(out.parent, "hud_cache", f))
    else:
        series(sys.argv[2], sys.argv[3])
