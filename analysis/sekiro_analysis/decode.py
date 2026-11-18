"""Is video decoded here exactly as in the research?

OpenCV decodes video with the FFmpeg build bundled in its wheel, and FFmpeg's conversion of the decoded YUV frames to
BGR has changed between versions. The Linux opencv-python-headless 5.0.0.93 wheel (FFmpeg 8) gives pixels up to 21
levels away from those of the Windows 5.0.0.93 wheel the research ran with (FFmpeg 7.1); on one recording that brought
back a false damage event the research had removed. The Linux 4.12.0.88 wheel (FFmpeg 5.1) gives exactly the
research's pixels (analysis/requirements.txt). Every step reads the HUD and the boss from these pixels, so the worker
runs the pipeline only where the decoding is the research's.

SAMPLE is a synthetic clip, not game footage: six frames of FFmpeg's testsrc2 pattern, 320×180, HEVC, full range and
BT.709 like the owner's recordings. DIGEST is the SHA-256 of its frames as the research decodes them, read in order
like the pipeline reads a video.

    python -m sekiro_analysis.decode      exit status 1 when this OpenCV decodes differently
"""
import hashlib
import sys
from pathlib import Path

import cv2

SAMPLE = Path(__file__).with_name("decode_sample.mp4")
DIGEST = "471a2772be72d792aa99a301a619b5b728fb10848ecd6931fb9a249636902fe5"


def digest(video=SAMPLE):
    """SHA-256 of all decoded frames, or None when nothing could be decoded."""
    cap = cv2.VideoCapture(str(video))
    h, n = hashlib.sha256(), 0
    while cap.grab():
        ok, frame = cap.retrieve()
        if not ok:
            break
        h.update(frame.tobytes())
        n += 1
    cap.release()
    return h.hexdigest() if n else None


def same_as_research():
    return digest() == DIGEST


if __name__ == "__main__":
    found = digest()
    print(f"OpenCV {cv2.__version__}: {SAMPLE.name} decodes to {found}")
    if found != DIGEST:
        sys.exit(f"not the research's decoding ({DIGEST}): the pipeline's results would differ")
