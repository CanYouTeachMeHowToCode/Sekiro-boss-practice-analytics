"""Is an upload a castle Genichiro fight? Research tools for the upload check of V4 M3.

Usage:
    python -I content_check.py templates     cut the boss-name templates from the owner's recordings
    python -I content_check.py scene-refs    scene features of the castle roof, from the development recordings
    python -I content_check.py check <video> [--write <out.json>]
    python -I content_check.py eval          every registered recording (all castle fights) and the clips in OTHER_CLIPS

The check itself (what is read, the thresholds, the reject codes) is in the analysis package,
analysis/sekiro_analysis/content_check.py, which the recording worker runs too. Here: where the templates are cut, the
owner's reject clips, and the evaluation. The templates and the scene features are cut from game frames, so they stay
local in work/content/, like the 死 mask (built again by the first two commands).
"""
import configparser
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, WORK, recordings, video_path  # noqa: E402
from sekiro_analysis import content_check as cc  # noqa: E402
from sekiro_analysis.content_check import (NAME_PCT, PLAY_X, PLAY_Y, SAMPLE_S, SCENE_Y, THRESHOLDS,  # noqa: E402,F401
                                           Scene, frames, hud_state, name_score, name_strip, text_box, window)
from sekiro_analysis.overlay_mask import mask_overlay  # noqa: E402

OUT = WORK / "content"
# where each template is cut: (interface, phase group, recording file under recordings_dir, time in seconds)
TEMPLATE_SOURCES = [
    ("zh-Hans", "1-2", "测试录像/测试录像13.mp4", 20.0),
    ("zh-Hans", "3", "测试录像/测试录像5.mp4", 180.0),       # phase 3 from 172 s
    ("zh-Hant", "1-2", "不同情景测试录像/繁体中文弦一郎.mp4", 20.0),
    ("zh-Hant", "3", "不同情景测试录像/繁体中文弦一郎.mp4", 260.0),
    ("en", "1-2", "不同情景测试录像/英文弦一郎.mp4", 20.0),
    ("en", "3", "不同情景测试录像/英文弦一郎.mp4", 200.0),
]
# clips that are not castle Genichiro fights, with what the check should say (the owner's, 2026-11-13)
OTHER_CLIPS = [
    ("不同情景测试录像/心中的弦一郎.mp4", "reject", "心中的弦一郎 (Reflection of Strength), same roof"),
    ("不同情景测试录像/最终战芦苇地弦一郎.mp4", "reject", "Isshin fight, first phase: 巴流 苇名弦一郎 in the reeds"),
    ("不同情景测试录像/无关视频.mp4", "reject", "another Sekiro boss on the castle roofs (1080p, 120 fps: the format check rejects it first)"),
    ("不同情景测试录像/无关视频2.mp4", "reject", "another game (1080p, 120 fps: the format check rejects it first)"),
]
# the package's reject codes, as the research reports have always written them
REASONS = {cc.NOT_SEKIRO: "no Sekiro HUD", cc.NO_BOSS: "no boss HP bar",
           cc.NOT_CASTLE_GENICHIRO: "boss name is not castle Genichiro", cc.NOT_CASTLE_ROOF: "not the castle roof"}


def recordings_dir():
    config = configparser.ConfigParser()
    config.read(GT / "local.config", encoding="utf-8")
    return Path(config["paths"]["recordings_dir"])


def build_templates():
    import cv2
    out = {}
    for ui, group, name, t in TEMPLATE_SOURCES:
        path = recordings_dir() / name
        best = None
        for tt, f in window(path, t - 3, t + 3):      # recordings without the overlay: the name is read unmasked
            hud, boss = hud_state(mask_overlay(f))
            if not boss:
                continue
            g = name_strip(f)
            box = text_box(g)
            if box is None:
                continue
            # the frame with the darkest background behind the name, where the text stands out most
            key = (-float(np.median(g[g < 170])) if (g < 170).any() else -255.0,)
            if best is None or key > best[0]:
                best = (key, tt, g[box[0]:box[1], box[2]:box[3]], box)
        if best is None:
            sys.exit(f"no boss name found in {name} near {t}")
        _, tt, tpl, box = best
        out[f"{ui}|{group}"] = tpl
        out[f"{ui}|{group}|box"] = np.array(box)
        print(f"{ui} phase {group}: {name} at {tt:.1f} s, text box {box}, {tpl.shape[1]}×{tpl.shape[0]}")
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "name_templates.npz", **out)
    for k, v in out.items():
        if not k.endswith("box"):
            cv2.imwrite(str(OUT / f"name_{k.replace('|', '_')}.png"), v)


def load_templates():
    return cc.load_templates(OUT / "name_templates.npz")


def build_scene_refs():
    scene, feats, owner = Scene(), [], []
    for rec_id, rec in recordings().items():
        if rec.get("set") != "development":
            continue
        masked = (mask_overlay(f) for _, f in frames(video_path(rec), 10.0))
        imgs = [f for f in masked if hud_state(f)[1]]
        feats.append(scene(imgs))
        owner += [rec_id] * len(imgs)
        print(f"{rec_id}: {len(imgs)} frames")
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "scene_refs.npz", feats=np.concatenate(feats), rec=np.array(owner))


def check(video, rec_id=None, scene=None, templates=None, overlay=False):
    """Scores for one video (see the package's check()), with the references in work/content."""
    return cc.check(video, scene or Scene(), templates or load_templates(), OUT / "scene_refs.npz", rec_id, overlay)


def verdict(res, th=THRESHOLDS):
    code = cc.verdict(res, th)
    return ("reject", REASONS[code]) if code else ("accept", "")


def evaluate():
    scene, templates = Scene(), load_templates()
    rows = []
    for rec_id, rec in recordings().items():
        res = check(video_path(rec), rec_id, scene, templates, bool(rec.get("overlay")))
        res["verdict"], res["reason"] = verdict(res)
        rows.append((rec_id, rec.get("set"), "accept", res))
        print(rec_id, json.dumps(res, ensure_ascii=False), flush=True)
    for name, want, what in OTHER_CLIPS:
        res = check(recordings_dir() / name, None, scene, templates)
        res["verdict"], res["reason"] = verdict(res)
        rows.append((name, what, want, res))
        print(name, json.dumps(res, ensure_ascii=False), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eval.json").write_text(json.dumps([{"video": a, "about": b, "want": c, **d} for a, b, c, d in rows],
                                              ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "templates":
        build_templates()
    elif cmd == "scene-refs":
        build_scene_refs()
    elif cmd == "eval":
        evaluate()
    elif cmd == "check":
        res = check(Path(sys.argv[2]))
        res["verdict"], res["reason"] = verdict(res)
        print(json.dumps(res, ensure_ascii=False))
