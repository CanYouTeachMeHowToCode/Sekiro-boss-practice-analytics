"""Is an upload a castle Genichiro fight? The upload check of V4 M3, as a research prototype.

Usage:
    python -I content_check.py templates     cut the boss-name templates from the owner's recordings
    python -I content_check.py scene-refs    scene features of the castle roof, from the development recordings
    python -I content_check.py check <video> [--write <out.json>]
    python -I content_check.py eval          every registered recording (all castle fights) and the clips in OTHER_CLIPS

A video passes when three things hold, checked on a frame every SAMPLE_S seconds:
1. Sekiro's HUD: Wolf's HP bar (hud_read.read_hp) shows in at least MIN_HUD of the frames. Otherwise: another game or
   an unrelated video.
2. The boss name under the boss HP bar is castle Genichiro's in one of the three supported interfaces: 苇名弦一郎 /
   巴流 苇名弦一郎 (Simplified), 葦名弦一郎 / 巴流　葦名弦一郎 (Traditional), Genichiro Ashina / Genichiro, Way of Tomoe
   (English). Each frame with the boss bar is matched against templates cut from the owner's recordings (normalised
   cross-correlation, a few pixels of play); the video's score is a high percentile of the per-frame best score, since
   snow, lightning and the sun wash the name out in some frames. This rejects other bosses and 心中的弦一郎, the
   Reflection of Strength fight on the same roof (owner, 2026-11-13: not castle Genichiro).
3. The scene is the castle roof: each frame's DINOv2 class token (HUD bands cut off) against those of frames from the
   development recordings, the nearest one by cosine; the video's score is the median. This rejects the Isshin fight,
   whose first phase is also 巴流 苇名弦一郎 but in a field of reeds (plan_m3.md, decision 9).

Frames are scaled to 2560×1440 first, so the fixed positions hold at any 16:9 resolution. The HUD and the scene are
read from frames that went through mask_overlay(), like everywhere in the pipeline. The boss name sits where the mask
is: it is read unmasked from recordings without the overlay (no animation lines there, so nothing of the answer leaks),
and not at all from the dev-menu recordings. The templates and the scene features are cut from game frames, so they stay local in
work/content/, like the 死 mask (built again by the first two commands). Thresholds are set from the castle recordings
and the owner's reject clips; they are proposals until the owner has seen the scores.
"""
import configparser
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, WORK, recordings, video_path  # noqa: E402
from hud_read import BOSS_ROWS, BOSS_X0, BOSS_X1, HP_ROWS, HP_X0, HP_X1, columns, read_boss, read_hp  # noqa: E402
from overlay_mask import BASE_H, BASE_W, mask_overlay  # noqa: E402

OUT = WORK / "content"
SAMPLE_S, MAX_SAMPLES = 2.0, 200
MIN_HUD = 0.3
# set from eval (2026-11-13): castle recordings name 0.970-0.998, scene 0.742-0.789; 心中的弦一郎 name 0.121;
# the reed field scene 0.490
THRESHOLDS = {"name": 0.80, "scene": 0.65}
NAME_BOX = (156, 216, 140, 760)          # y0, y1, x0, x1 at 2560×1440: the boss name under the boss HP bar
PLAY_X, PLAY_Y = 8, 6
NAME_PCT = 75
SCENE_Y = (230, 1180)                    # rows kept for the scene: below the boss bar, above Wolf's HP and posture bars
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
]


def recordings_dir():
    config = configparser.ConfigParser()
    config.read(GT / "local.config", encoding="utf-8")
    return Path(config["paths"]["recordings_dir"])


def prepare(f):
    """The frame scaled to 2560×1440, not masked: the caller masks it (see Frame)."""
    if f.shape[:2] != (BASE_H, BASE_W):
        f = cv2.resize(f, (BASE_W, BASE_H), interpolation=cv2.INTER_AREA)
    return f


def frames(video, step_s=SAMPLE_S, limit=MAX_SAMPLES):
    """(time, frame scaled to 2560×1440 and masked) every step_s seconds, at most limit of them, spread evenly."""
    cap = cv2.VideoCapture(str(video))
    fps, n = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if not fps or not n:
        return
    for t in np.arange(0, n / fps, max(step_s, n / fps / limit)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, f = cap.read()
        if ok:
            yield float(t), prepare(f)


def window(video, t0, t1, every=6):
    """Every `every`-th frame between t0 and t1 seconds, read in order after one seek."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(t0, 0) * fps))
    i = int(max(t0, 0) * fps)
    while i <= t1 * fps:
        ok, f = cap.read()
        if not ok:
            return
        if i % every == 0:
            yield i / fps, prepare(f)
        i += 1


def name_strip(frame):
    """The boss-name strip of an unmasked frame. The overlay mask covers it, but only the dev-menu recordings have
    animation lines there; a recording without the overlay (every upload) has just the name, so its strip is read as
    is. A dev-menu recording keeps its mask and skips the name check."""
    y0, y1, x0, x1 = NAME_BOX
    return cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)


def text_box(gray):
    """Bounding box of the bright text in a name strip, padded: (y0, y1, x0, x1) inside the strip."""
    mask = (gray >= 170).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    ys, xs = np.nonzero(mask)
    if len(xs) < 30:
        return None
    pad = 3
    return (max(ys.min() - pad, 0), min(ys.max() + pad + 1, gray.shape[0]),
            max(xs.min() - pad, 0), min(xs.max() + pad + 1, gray.shape[1]))


def hud_state(frame):
    hud, _, _ = read_hp(columns(frame, HP_ROWS, HP_X0, HP_X1))
    boss, _, _ = read_boss(columns(frame, BOSS_ROWS, BOSS_X0, BOSS_X1))
    return hud, boss


def build_templates():
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
    d = np.load(OUT / "name_templates.npz")
    return [(k, d[k], d[k + "|box"]) for k in d.files if not k.endswith("box")]


def name_score(frame, templates):
    """Best normalised cross-correlation of the frame's name strip with any template, and which template."""
    g = name_strip(frame).astype(np.float32)
    best, which = -1.0, None
    for key, tpl, box in templates:
        y0, y1, x0, x1 = (int(v) for v in box)
        ys, xs = max(y0 - PLAY_Y, 0), max(x0 - PLAY_X, 0)
        region = g[ys:min(y1 + PLAY_Y, g.shape[0]), xs:min(x1 + PLAY_X, g.shape[1])]
        if region.shape[0] < tpl.shape[0] or region.shape[1] < tpl.shape[1]:
            continue
        s = float(cv2.matchTemplate(region, tpl.astype(np.float32), cv2.TM_CCOEFF_NORMED).max())
        if s > best:
            best, which = s, key
    return best, which


class Scene:
    """DINOv2 small14 class tokens of the scene part of a frame."""

    def __init__(self):
        import timm
        import torch
        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=True, num_classes=0,
                                       img_size=224).eval().to(self.dev)
        self.mean = torch.tensor((0.485, 0.456, 0.406), device=self.dev).view(1, 3, 1, 1)
        self.std = torch.tensor((0.229, 0.224, 0.225), device=self.dev).view(1, 3, 1, 1)

    def __call__(self, imgs):
        torch = self.torch
        crops = np.stack([cv2.resize(f[SCENE_Y[0]:SCENE_Y[1]], (398, 224), interpolation=cv2.INTER_AREA)
                          for f in imgs])
        with torch.no_grad():
            x = torch.from_numpy(crops[..., ::-1].copy()).to(self.dev).permute(0, 3, 1, 2).float() / 255
            x = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", antialias=True, align_corners=False)
            cls = self.model.forward_features((x - self.mean) / self.std)[:, 0]
            return torch.nn.functional.normalize(cls, dim=1).cpu().numpy()


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
    """Scores for one video. rec_id leaves that recording's own frames out of the scene references; overlay (a dev-menu
    recording) skips the name, which the overlay mask covers."""
    templates = templates or load_templates()
    scene = scene or Scene()
    refs = np.load(OUT / "scene_refs.npz")
    keep = refs["rec"] != (rec_id or "")
    ref_feats = refs["feats"][keep]
    n = hud_n = 0
    names, which, imgs = [], {}, []
    for t, raw in frames(video):
        n += 1
        f = mask_overlay(raw)
        hud, boss = hud_state(f)
        hud_n += hud
        if boss and not overlay:
            s, k = name_score(raw, templates)
            names.append(s)
            which[k] = which.get(k, 0) + 1
        if hud:
            imgs.append(f)
    sims = []
    for i in range(0, len(imgs), 64):
        sims += list((scene(imgs[i:i + 64]) @ ref_feats.T).max(1))
    res = {"frames": n, "hud": hud_n / n if n else 0.0, "boss_frames": len(names), "name_checked": not overlay,
           "name": float(np.percentile(names, NAME_PCT)) if names else None,
           "name_match": max(which, key=which.get) if which else None,
           "scene": float(np.median(sims)) if sims else None}
    return res


def verdict(res, th=THRESHOLDS):
    if res["hud"] < MIN_HUD:
        return "reject", "no Sekiro HUD"
    if res["name_checked"] and res["name"] is None:
        return "reject", "no boss HP bar"
    if res["name_checked"] and res["name"] < th["name"]:
        return "reject", "boss name is not castle Genichiro"
    if res["scene"] is None or res["scene"] < th["scene"]:
        return "reject", "not the castle roof"
    return "accept", ""


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
