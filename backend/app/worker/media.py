"""ffprobe and ffmpeg: what a video is, and short clips cut from it."""

import json
import shutil
import statistics
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


class MediaError(RuntimeError):
    """ffprobe could not read the file, or ffmpeg could not cut it."""


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration_s: float
    # the transfer function ffprobe names (bt709, smpte2084 = HDR10's PQ, arib-std-b67 = HLG), when the file says
    transfer: str | None = None
    # share of frame intervals far from the usual one (frame_irregularity); None when not measured
    irregular: float | None = None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(path: Path) -> VideoInfo:
    """The size, frame rate, length and transfer function of a video's first video stream."""
    entries = "stream=width,height,avg_frame_rate,r_frame_rate,color_transfer:format=duration"
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of", "json", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True).stdout
        data = json.loads(out)
        stream = data["streams"][0]
        rate = stream.get("avg_frame_rate")
        if not rate or rate == "0/0":
            rate = stream["r_frame_rate"]
        return VideoInfo(width=int(stream["width"]), height=int(stream["height"]), fps=float(Fraction(rate)),
                         duration_s=float(data["format"]["duration"]), transfer=stream.get("color_transfer"),
                         irregular=frame_irregularity(path))
    except (subprocess.SubprocessError, OSError, KeyError, IndexError, ValueError, ZeroDivisionError) as exc:
        raise MediaError(f"cannot read {path.name}: {exc}") from exc


def frame_irregularity(path: Path) -> float | None:
    """The share of frame intervals more than a quarter off the usual one, from the video packets' timestamps
    (nothing is decoded): about 0 at a constant frame rate, where a dropped frame now and then adds a little (at most
    0.2% on the owner's recordings, 2026-11-18), and large at a variable one. None for a video too short to tell.
    The header's rates cannot tell: a constant 60 fps recording can declare r_frame_rate 240."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0",
           str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True).stdout
    pts = sorted(float(x) for x in out.replace(",", " ").split() if x != "N/A")
    gaps = [b - a for a, b in zip(pts, pts[1:])]
    if len(gaps) < 10:
        return None
    usual = statistics.median(gaps)
    if usual <= 0:
        return None
    return sum(abs(g - usual) > 0.25 * usual for g in gaps) / len(gaps)


CLIP_HEIGHT = 720


def cut_clip(video: Path, start_s: float, end_s: float, out: Path) -> None:
    """A clip from start_s to end_s, as 720p H.264 (with AAC sound when the video has sound), which every browser
    plays, whatever the upload's codec; faststart so playback can begin before the whole clip has loaded."""
    out.parent.mkdir(parents=True, exist_ok=True)
    start = max(0.0, start_s)           # a failure in the first seconds: the clip starts with the video
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video),
           "-t", f"{max(0.1, end_s - start):.3f}", "-vf", f"scale=-2:{CLIP_HEIGHT}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
    except (subprocess.SubprocessError, OSError) as exc:
        out.unlink(missing_ok=True)
        detail = getattr(exc, "stderr", "") or exc
        raise MediaError(f"cannot cut a clip from {video.name}: {detail}") from exc
