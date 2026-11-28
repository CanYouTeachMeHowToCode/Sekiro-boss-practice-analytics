"""Local research (never commit: renders of game models): one clip per catalog chain branch, and an HTML gallery.

Usage: python -I gallery.py <worker index> <worker count>     (each worker renders its share of the catalog entries)
       python -I gallery.py page                               (writes out/gallery/index.html from the clips there)
Chains come from the approved catalog; a branch is played animation by animation with root motion chained. Where an
animation hands over to the next one is not known without a recording: a non-final animation is cut 0.4 s after its
last damage window (attack, throw or bullet) closes, or played to its end when it has none; the last one plays in full.
Camera: 5 m in front of the boss's starting position, 1.7 m up, following the boss's centre; X mirrored (the data is
left-handed). Red while an attack or throw window is open.
"""
import csv
import html
import itertools
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHR as GAME, GT, GT_WORK, RENDER, exe, tool_env  # noqa: E402

EXE = exe("posexport")
OUT = RENDER / "gallery"
CHR = {"c7100": {"skip": set(), "cape": "27"}, "c7110": {"skip": {10, 11}, "cape": ""}}   # castle display masks, cape
C = 420
FOCAL = (C / 2) / np.tan(np.radians(50) / 2)


def parse(s):
    """Chain text -> nested ("seq", items) | ("alt", [(cond, seq)]) | ("anim", id), as chain_check.py."""
    i = 0

    def ws():
        nonlocal i
        while i < len(s) and s[i] == " ":
            i += 1

    def seq():
        nonlocal i
        items = []
        while True:
            ws()
            if s[i] == "[":
                items.append(alt())
            elif s[i] == "—":
                i += 1
            else:
                m = re.match(r"\d+", s[i:])
                items.append(("anim", int(m.group())))
                i += len(m.group())
            ws()
            if i < len(s) and s[i] == "→":
                i += 1
                continue
            return ("seq", items)

    def alt():
        nonlocal i
        i += 1
        branches = []
        while True:
            j = s.index(":", i)
            cond = s[i:j].strip()
            i = j + 1
            branches.append((cond, seq()))
            ws()
            if s[i] == "｜":
                i += 1
                continue
            i += 1
            return ("alt", branches)
    return seq()


def expand(node):
    """Every animation sequence of a chain: each alternative branch; an optional branch (one condition, no else) is
    taken, as it shows the full move (the throw's follow-up when the catch connects)."""
    if node[0] == "anim":
        return [[node[1]]]
    if node[0] == "alt":
        return [x for _, sub in node[1] for x in expand(sub)]
    out = [[]]
    for item in node[1]:
        out = [a + b for a in out for b in expand(item)]
    return out


def windows(char):
    w = {}
    for r in csv.DictReader(open(GT / "engine" / "genichiro_attack_windows.csv", encoding="utf-8")):
        if r["character"] == char and r["kind"] in ("attack", "throw", "bullet"):
            w.setdefault(int(r["anim"]), []).append((r["kind"], float(r["start_s"]), float(r["end_s"])))
    return w


_TAE = {}


def hkx_of(char, anim):
    """The animation file a TAE entry plays: an import plays its source's file, and an entry may name another file."""
    if char not in _TAE:
        import json
        path = GT_WORK / f"{char}_tae.json"
        _TAE[char] = {a["id"]: a for a in json.load(open(path, encoding="utf-8"))["animations"]}
    a = _TAE[char][f"a000_{anim:06d}"]
    while a["kind"] == "import_other_anim":
        a = _TAE[char][a["imports_from"]]
    return int((a.get("hkx") or a["id"])[5:])


def export(char, anim, tmp, last_frame):
    anim = hkx_of(char, anim)
    env = tool_env(SKIP_PAST="1", CAPE_MESHES=CHR[char]["cape"])
    subprocess.run([str(EXE), str(GAME / f"{char}.chrbnd.dcx"), str(GAME / f"{char}.anibnd.dcx"), str(tmp), f"{anim:06d}",
                    f"0-{last_frame}"], env=env, check=True, capture_output=True)
    root = np.loadtxt(tmp / f"{char}_a{anim:06d}_root.csv", delimiter=",").reshape(-1, 4, 4)
    return root


def render(V, T, hot, cam):
    V = V * np.array([-1, 1, 1], np.float32)
    target = V.mean(0)
    fwd = (target - cam) / np.linalg.norm(target - cam)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = V - cam
    P = np.stack([rel @ right, rel @ up, rel @ fwd], -1)
    tri = P[T]
    tri = tri[tri[:, :, 2].min(1) > 0.1]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    g = 40 + 190 * (0.25 + 0.75 * np.abs(n[:, 2]))
    xy = np.stack([C / 2 + FOCAL * tri[:, :, 0] / tri[:, :, 2], C / 2 - FOCAL * tri[:, :, 1] / tri[:, :, 2]], -1)
    xy = np.clip(xy, -4 * C, 5 * C).round().astype(np.int32)
    img = np.full((C, C, 3), 255, np.uint8)
    for i in np.argsort(-tri[:, :, 2].mean(1)):
        col = (int(g[i] * 0.55), int(g[i] * 0.55), int(min(255, g[i] * 1.1))) if hot else (int(g[i]),) * 3
        cv2.fillConvexPoly(img, xy[i], col, cv2.LINE_AA)
    return img


def render_ortho(V, T, hot, lo, hi, view):
    """Orthographic grey render of mirrored world vertices: front looks along +Z (screen right = -X... after the mirror,
    the boss's own left/right read as in the game), side looks along -X; the frame fits the clip's whole box."""
    if view == "front":
        h, d, sign = 0, 2, -1.0      # horizontal axis X (flipped so the camera at -Z sees it like the player), depth Z
    else:
        h, d, sign = 2, 0, -1.0      # horizontal axis Z (camera on the boss's right, +X, looking -X: screen right = -Z), depth X
    W = C if view == "front" else 2 * C          # the side panel is twice as wide: it holds the distance travelled
    s = 0.9 * min(W / (hi[h] - lo[h] + 1e-6), C / (hi[1] - lo[1] + 1e-6))
    cx, cy = (lo[h] + hi[h]) / 2, (lo[1] + hi[1]) / 2
    tri = V[T]
    x = W / 2 + sign * (tri[:, :, h] - cx) * s
    y = C / 2 - (tri[:, :, 1] - cy) * s
    depth = tri[:, :, d].mean(1) * (1.0 if view == "front" else -1.0)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    g = 40 + 190 * (0.25 + 0.75 * np.abs(n[:, d]))
    img = np.full((C, W, 3), 255, np.uint8)
    ground = int(round(C / 2 - (0 - cy) * s))
    cv2.line(img, (0, ground), (W - 1, ground), (200, 200, 200), 1)
    xy = np.stack([x, y], -1).round().astype(np.int32)
    for i in np.argsort(-depth):       # far first: the camera looks from the low-depth side
        col = (int(g[i] * 0.55), int(g[i] * 0.55), int(min(255, g[i] * 1.1))) if hot else (int(g[i]),) * 3
        cv2.fillConvexPoly(img, xy[i], col, cv2.LINE_AA)
    return img


def clip(char, entry, k, anims, T, wins):
    tmp = RENDER / f"tmp_{entry}_{k}"
    tmp.mkdir(parents=True, exist_ok=True)
    plan, B = [], np.eye(4)
    for j, a in enumerate(anims):
        root = export(char, a, tmp, 600)
        n = len(root)
        if j < len(anims) - 1 and wins.get(a):
            n = min(n, int(round((max(e for _, _, e in wins[a]) + 0.4) * 30)) + 1)
        plan.append((a, n, root, B.copy()))
        B = root[n - 1] @ B
    def frames():
        for a, n, root, base in plan:
            for f in range(n):
                V = np.fromfile(tmp / f"{char}_a{hkx_of(char, a):06d}_f{f}.bin", np.float32).reshape(-1, 3)
                V = (np.hstack([V, np.ones((len(V), 1), np.float32)]) @ (root[f] @ base))[:, :3]
                yield a, f, V * np.array([-1, 1, 1], np.float32)     # the data is left-handed: mirror X

    # fixed orthographic views framing the whole clip: front (from the player's side, -Z) and side (from the boss's
    # right); the camera neither follows nor zooms, so distance travelled and turns show as they are
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for _, _, V in frames():
        lo, hi = np.minimum(lo, V[::8].min(0)), np.maximum(hi, V[::8].max(0))
    lo[1] = min(lo[1], 0.0)
    out = OUT / f"{entry}_{k}.webm"
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"VP80"), 30, (3 * C, C + 30))
    for a, f, V in frames():
        on = [kd for kd, s, e in wins.get(a, []) if kd != "bullet" and s - 1 / 60 <= f / 30 <= e + 1 / 60]
        head = np.full((30, 3 * C, 3), 255, np.uint8)
        cv2.putText(head, f"{entry}  {a:04d} +{f / 30:.2f}s" + (f"  {on[0]}" if on else "") + "     front | side",
                    (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200) if on else (0, 0, 0), 1, cv2.LINE_AA)
        views = [render_ortho(V, T, bool(on), lo, hi, axis) for axis in ("front", "side")]
        vw.write(np.vstack([head, np.hstack(views)]))
    vw.release()
    shutil.rmtree(tmp)
    return out


def catalog():
    rows = [r for r in csv.DictReader(open(GT / "semantic" / "genichiro_catalog.csv", encoding="utf-8")) if r["kind"] == "move"]
    names = {}
    for m in csv.DictReader(open(GT / "semantic" / "genichiro_product_moveset.csv", encoding="utf-8")):
        for e in m["catalog_entries"].split():
            names.setdefault(e, []).append(m["name_zh"])
    return rows, names


def tris(char):
    src = RENDER / char / f"{char}_tris.csv"
    if not src.exists():          # the model's triangles, once per character (meshexport)
        subprocess.run([str(exe("meshexport")), str(GAME / f"{char}.chrbnd.dcx"), str(src.parent)], env=tool_env(),
                       check=True, capture_output=True)
    return np.array([[int(r["a"]), int(r["b"]), int(r["c"])] for r in csv.DictReader(open(src))
                     if int(r["mesh"]) not in CHR[char]["skip"]], np.int64)


def page():
    rows, names = catalog()
    parts = ["<!doctype html><meta charset='utf-8'><title>Genichiro catalog clips</title>",
             "<style>body{font-family:sans-serif;margin:16px}td{vertical-align:top;padding:6px;border-bottom:1px solid #ddd}"
             "video{width:280px}</style>",
             "<h1>天守阁弦一郎：招式目录渲染片段（本机，不进仓库）</h1>",
             "<p>每行一个目录条目；有分支的链每个分支一段。链里动画的切换点是估的（上一个动画最后一次伤害判定结束后 0.4 秒），"
             "左边正面（狼的方向）、右边侧面（从 Boss 右手边看），两个镜头都固定不动、没有透视，框住整段片段走过的范围；灰线是地面。红色 = TAE 伤害判定。</p><table>"]
    for r in rows:
        vids = sorted(OUT.glob(f"{r['entry']}_*.webm"))
        cells = "".join(f"<video src='{v.name}' controls loop muted preload='none'></video>" for v in vids)
        parts.append(f"<tr><td><b>{r['entry']}</b><br>阶段 {html.escape(r['phases'])}<br>"
                     f"{html.escape('、'.join(names.get(r['entry'], ['（产品里没有）'])))}</td>"
                     f"<td>{html.escape(r['chain'])}<br><small>{html.escape(r['owner_labels'])}</small></td><td>{cells}</td></tr>")
    parts.append("</table>")
    (OUT / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print("wrote", OUT / "index.html")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "page":
        page()
        sys.exit()
    w, nw = int(sys.argv[1]), int(sys.argv[2])
    rows, _ = catalog()
    T = {c: tris(c) for c in CHR}
    W = {c: windows(c) for c in CHR}
    for r in rows[w::nw]:
        char = r["character"]
        seqs = expand(parse(r["chain"]))[:3]
        for k, anims in enumerate(seqs):
            if (OUT / f"{r['entry']}_{k}.webm").exists():
                continue
            out = clip(char, r["entry"], k, anims, T[char], W[char])
            print(r["entry"], k, "→".join(map(str, anims)), out.name, flush=True)
