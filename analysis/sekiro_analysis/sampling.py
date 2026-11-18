"""How often the steps read a video, whatever its frame rate (version 3, 2026-11-18).

Version 2 was built and measured on 60 fps recordings read every other frame: 30 samples a second. Every constant that
counts samples means a 30th of a second: events.py's LINE_HOLD and LINE_GAP, moves.py's RATE (crops per second) and the
windows it turns into rows. At 30 fps, every other frame gave 15 samples a second, so those windows covered twice the
time and the boss's motion ran at twice the references' speed. step() keeps 30 samples a second at any frame rate:
every frame at 30 fps, every other at 60 (the same frames as version 2, so a 60 fps video's outputs do not change).

The steps that sample at other rates (reversal.py at 20 a second, content_check.window at 10) use every() the same way.
Both work from the nominal rate, the multiple of 30 nearest the file's (29.97 and 30 are 30; 59.94 and 60 are 60), so
two files of one recorder setting are read alike. Frame numbers still turn into seconds with the file's own rate.
"""
import cv2

SAMPLES_PER_S = 30
# what version 2 assumed for every video, kept for a file whose rate cannot be read
DEFAULT_FPS = 60


def nominal(fps):
    """The multiple of 30 nearest the frame rate: 30, 60, 90, 120..."""
    if not fps or fps <= 0:
        return DEFAULT_FPS
    return SAMPLES_PER_S * max(1, round(fps / SAMPLES_PER_S))


def every(fps, per_second):
    """Read every n-th frame to get about `per_second` samples a second; never less than every frame. Halves round up,
    so 30 fps read at 20 a second takes every other frame."""
    return max(1, int(nominal(fps) / per_second + 0.5))


def step(fps):
    """Every n-th frame for 30 samples a second: 2 at 60 fps (as in version 2), 1 at 30 fps."""
    return nominal(fps) // SAMPLES_PER_S


def video_fps(video):
    """The frame rate OpenCV reads from the file: the rate the steps turn frame numbers into seconds with."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps
