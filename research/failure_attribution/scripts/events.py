"""Find Wolf's failure events in the HUD series (the rules: analysis/sekiro_analysis/events.py).

Usage: python -I events.py <hud.csv> <out.csv>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402,F401  (puts the analysis package on the path)
from sekiro_analysis.events import *  # noqa: E402,F401,F403
from sekiro_analysis.events import write_events  # noqa: E402

if __name__ == "__main__":
    write_events(sys.argv[1], sys.argv[2])
