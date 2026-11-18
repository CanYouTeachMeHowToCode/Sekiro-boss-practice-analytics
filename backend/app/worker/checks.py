"""The format an upload must have before it is analysed (owner decisions, 2026-10-25).

Supported: 16:9, 720p to 4K, a constant 30 or 60 frames per second, at most 10 minutes. The checks that it is a castle
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
# The attribution was measured on 60 fps recordings only. Others are analysed (version 3 reads 30 samples a second at
# any rate), but the report says their results are for reference only until they are measured too (owner decision,
# 2026-11-18).
VALIDATED_FRAME_RATES = (60.0,)
# A variable frame rate: more than this share of frame intervals far from the usual one (media.frame_irregularity;
# at most 0.2% on the owner's constant-rate recordings). The steps turn frame numbers into seconds with one rate.
MAX_IRREGULAR = 0.05
# HDR video (PQ or HLG) is rejected until a real HDR recording shows how to map it to the colours the analysis was
# measured on (owner decision, 2026-11-17)
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}


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
    if info.irregular is not None and info.irregular > MAX_IRREGULAR:
        return "variable_frame_rate"
    if not any(abs(info.fps - rate) <= FRAME_RATE_TOLERANCE for rate in FRAME_RATES):
        return "unsupported_frame_rate"
    if info.transfer in HDR_TRANSFERS:
        return "hdr"
    return None


def validated_frame_rate(fps: float | None) -> bool:
    """Whether the attribution was measured at this frame rate (unknown counts as validated: nothing to warn about)."""
    return fps is None or any(abs(fps - rate) <= FRAME_RATE_TOLERANCE for rate in VALIDATED_FRAME_RATES)
