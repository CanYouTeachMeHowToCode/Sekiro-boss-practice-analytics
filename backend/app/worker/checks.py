"""The format an upload must have before it is analysed (owner decisions, 2026-10-25).

Supported: 16:9, 720p to 4K, about 30 or 60 frames per second, at most 10 minutes. The checks that it is a castle
Genichiro fight (the Sekiro HUD, the boss's name, not the reed field before Isshin) come with reference images from
the owner's recordings.
"""

from app.worker.media import VideoInfo

MAX_DURATION_S = 600.0
MIN_HEIGHT, MAX_HEIGHT = 720, 2160
# Below this height a video is still analysed, but the boss shows too little detail for the move to be recognised as
# often: on 720p about half the failures get a sure move, against about 80% at 1080p (failures themselves are found
# as well). The upload page recommends at least 1080p and the report says so (owner decision, 2026-11-17).
RECOMMENDED_MIN_HEIGHT = 1080
ASPECT, ASPECT_TOLERANCE = 16 / 9, 0.01
FRAME_RATES, FRAME_RATE_TOLERANCE = (30.0, 60.0), 1.0


def format_problem(info: VideoInfo) -> str | None:
    """Why the analysis cannot take this video, as a reject code the frontend translates; None when it can."""
    if info.duration_s <= 0 or info.width <= 0 or info.height <= 0:
        return "unreadable"
    if info.duration_s > MAX_DURATION_S:
        return "too_long"
    if abs(info.width / info.height - ASPECT) > ASPECT_TOLERANCE:
        return "not_16_9"
    if not MIN_HEIGHT <= info.height <= MAX_HEIGHT:
        return "unsupported_resolution"
    if not any(abs(info.fps - rate) <= FRAME_RATE_TOLERANCE for rate in FRAME_RATES):
        return "unsupported_frame_rate"
    return None
