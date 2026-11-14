"""Simulated resolutions (V4 M3): the frozen analyzer on labelled test recordings scaled down to 1080p and 720p.

Usage: python -I sim_resolution.py make        scale the recordings and register the copies
       python -I sim_resolution.py run         hud_pipeline.py on every copy, then reliability.py report --set simulation
       python -I sim_resolution.py compare     the original against each copy, failure by failure

Before the analyzer is packaged for the upload worker, this shows whether it holds up at the resolutions M3 accepts
(16:9, 720p to 4K): the HUD positions are scaled from 2560×1440, the 死 mask was made at 1440p, and the boss crops are
matched against references that are all 1440p, so a smaller picture could lose events or moves. The copies are the
owner's test recordings scaled with ffmpeg (area filter, H.264 CRF 18, the bundled binary of imageio-ffmpeg), so they
keep the owner's labels; the game rendering at a lower resolution, and other recording software, can still differ,
which only real clips show.

The copies go to SIM_DIR (local, outside the repository) and into recordings.local.json (gitignored), with set
"simulation" and answers_of the original, so reliability.py reads the original's answers (common.annotation_dir).
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FA, HERE, recordings, video_path, work_dir  # noqa: E402

SIM_DIR = Path.home() / ".sekiro-research" / "sim_resolution"
SOURCES = ["2026-11-11-castle-1", "2026-11-11-castle-2", "2026-11-11-castle-6", "2026-11-11-castle-8"]
SIZES = [(1920, 1080), (1280, 720)]
LOCAL = FA / "recordings.local.json"


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make():
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    recs = recordings()
    entries = []
    for src in SOURCES:
        rec = recs[src]
        for w, h in SIZES:
            out = SIM_DIR / f"{src}-{h}p.mp4"
            if not out.exists():
                subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path(rec)),
                                "-vf", f"scale={w}:{h}:flags=area", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                                "18", "-pix_fmt", "yuv420p", "-an", str(out)], check=True)
            entries.append({"id": f"{src}-{h}p", "file_name": str(out), "ruleset": rec["ruleset"],
                            "game_version": rec["game_version"], "overlay": False, "set": "simulation",
                            "answers_of": src, "use": f"{src} scaled to {w}×{h} by sim_resolution.py"})
            print(f"{out.name}: {out.stat().st_size / 1e6:.0f} MB", flush=True)
    LOCAL.write_text(json.dumps({"recordings": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run():
    ids = [r for r, rec in recordings().items() if rec.get("set") == "simulation"]
    for rec_id in ids:
        subprocess.run([sys.executable, "-I", str(HERE / "hud_pipeline.py"), rec_id], check=True)
    subprocess.run([sys.executable, "-I", str(HERE / "reliability.py"), "report", "--set", "simulation"], check=True)


def compare():
    """Each original failure against the copies: which events were found, and the move answer."""
    def rows(rec_id):
        return list(csv.DictReader(open(work_dir(rec_id) / "failure_predictions.csv", encoding="utf-8")))
    for src in SOURCES:
        print(f"== {src}")
        base = rows(src)
        for w, h in SIZES:
            sim = rows(f"{src}-{h}p")
            same = sum(1 for a, b in zip(base, sim) if (a["move"], a["certain"]) == (b["move"], b["certain"]))
            print(f"  {h}p: {len(sim)} failures (original {len(base)}); same move and sureness on {same}")
            for b in sim:
                near = min(base, key=lambda a: abs(float(a["time_s"]) - float(b["time_s"])), default=None)
                if near is None or abs(float(near["time_s"]) - float(b["time_s"])) > 0.5 \
                        or (near["move"], near["certain"]) != (b["move"], b["certain"]):
                    print(f"    {float(b['time_s']):7.1f}s {b['type']:13s} {b['move']} sure={b['certain']}  original: "
                          + (f"{float(near['time_s']):.1f}s {near['move']} sure={near['certain']}" if near else "-"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"make": make, "run": run, "compare": compare}[sys.argv[1]]()
