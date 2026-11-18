"""The dev-menu overlay mask lives in the analysis package (analysis/sekiro_analysis/overlay_mask.py), shared with the
recording worker; this keeps the research imports and the check-image command working.

Usage (check image):  python -I overlay_mask.py <video> <seconds> <out.png>
"""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402,F401  (puts the analysis package on the path)
from sekiro_analysis.overlay_mask import BASE_H, BASE_W, MASK, mask_box, mask_overlay  # noqa: E402,F401

if __name__ == "__main__":
    runpy.run_module("sekiro_analysis.overlay_mask", run_name="__main__")
