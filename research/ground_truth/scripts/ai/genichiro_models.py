"""What the Genichiro-family character IDs are: the two combat models and the four others (c7101, c7102, c7103, c7111).

Usage: python -I genichiro_models.py <out.json>

Game files are read (read-only) from game_dir in research/ground_truth/local.config:
  chr/<id>.chrbnd|anibnd|behbnd.dcx    which archives exist; FLVER materials, bones, meshes; TAE entries; animations
  action/script/<id>.hks               behavior script and its hash
  map/mapstudio/*.msb.dcx              map parts named <id>_NNNN (placements)
  cutscene/*.cutscenebnd.dcx           cutscenes whose .mqb names a part <id>_NNNN
  event/*.emevd.dcx                    events that play each of those cutscenes (2002[xx], first argument)
For each non-combat model, the bones it has that its combat counterpart lacks are listed: a facial rig marks a
cutscene model. Cutscene sNN_MM_KKKK has ID NNMMKKKK in the event scripts.
The project owner confirmed the roles on 2026-10-12 after viewing the models in DS Anim Studio.
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))
sys.path.insert(0, str(HERE))
from bnd_names import LOCAL_CONFIG, read_dcx  # noqa: E402
import configparser  # noqa: E402
import emevd  # noqa: E402

out_path = Path(sys.argv[1])
cfg = configparser.ConfigParser()
cfg.read(LOCAL_CONFIG, encoding="utf-8")
GAME = Path(cfg["paths"]["game_dir"])
MODELS = ["c7100", "c7101", "c7102", "c7103", "c7110", "c7111"]
COUNTERPART = {"c7101": "c7100", "c7102": "c7100", "c7111": "c7110"}
ROLE = {  # confirmed by the project owner on 2026-10-12
    "c7100": "战斗模型:苇名弦一郎(着甲),天守阁一、二阶段、序章、心中的弦一郎第一段",
    "c7101": "过场模型:着甲的苇名弦一郎(带面部表情骨骼),没有战斗动作",
    "c7102": "过场道具:弦一郎的铠甲、头盔和披风,没有找到哪个过场引用它",
    "c7103": "空壳:没有模型和动画,行为文件是复制品,哪里都没有引用,很可能废弃",
    "c7110": "战斗模型:巴流 苇名弦一郎,天守阁三阶段、剑圣战第一阶段、心中的弦一郎第二段",
    "c7111": "过场模型:巴流 苇名弦一郎,没有战斗动作",
}


def bnd_files(b):
    count = struct.unpack_from("<I", b, 0x0C)[0]
    esz = struct.unpack_from("<Q", b, 0x20)[0]
    out = {}
    for i in range(count):
        off = 0x40 + i * esz
        size = struct.unpack_from("<Q", b, off + 0x08)[0]
        doff = struct.unpack_from("<I", b, off + 0x18)[0]
        noff = struct.unpack_from("<I", b, off + 0x20)[0]
        e = noff
        while b[e:e + 2] != b"\0\0":
            e += 2
        out[b[noff:e].decode("utf-16-le", "replace").split("\\")[-1]] = b[doff:doff + size]
    return out


def u16(b, o):
    e = o
    while b[e:e + 2] != b"\0\0":
        e += 2
    return b[o:e].decode("utf-16-le", "replace")


def flver(b):
    """FLVER2: dummy, material, bone and mesh counts at 0x14; materials (0x20 each) after the 0x80 header and the
    dummies (0x40 each); bones (0x80 each, name offset at +0x0C) after the materials."""
    dummies, mats, bones, meshes = struct.unpack_from("<iiii", b, 0x14)
    mo = 0x80 + dummies * 0x40
    materials = [u16(b, struct.unpack_from("<i", b, mo + i * 0x20)[0]) for i in range(mats)]
    bo = mo + mats * 0x20
    bone_names = [u16(b, struct.unpack_from("<i", b, bo + i * 0x80 + 0x0C)[0]) for i in range(bones)]
    return {"materials": materials, "bones": bone_names, "meshes": meshes}


sha = lambda b: hashlib.sha256(b).hexdigest()

# ---- archives
info = {}
for m in MODELS:
    rec = {"model": m, "role": ROLE[m], "archives": {}}
    for kind in ("chrbnd", "anibnd", "behbnd", "texbnd"):
        p = GAME / "chr" / f"{m}.{kind}.dcx"
        if not p.exists():
            continue
        if kind == "texbnd":
            rec["archives"][kind] = {}
            continue
        files = bnd_files(read_dcx(p))
        rec["archives"][kind] = {n: {"bytes": len(d), "sha256": sha(d)[:16]} for n, d in files.items()
                                 if not (n.startswith("a0") and n.endswith(".hkx"))}
        if kind == "chrbnd" and f"{m}.flver" in files:
            rec["_flver"] = flver(files[f"{m}.flver"])
        if kind == "anibnd":
            tae = files.get(f"{m}.tae")
            rec["tae_entries"] = struct.unpack_from("<i", tae, 0x54)[0] if tae else None
            rec["animations"] = sum(1 for n in files if n.startswith("a0") and n.endswith(".hkx"))
    hks = GAME / "action/script" / f"{m}.hks"
    rec["behavior_script_sha256"] = sha(hks.read_bytes())[:16] if hks.exists() else None
    info[m] = rec

for m, rec in info.items():
    f = rec.pop("_flver", None)
    rec["_bones"] = set(f["bones"]) if f else set()
    if f:
        rec["model_summary"] = {"materials": len(f["materials"]), "bones": len(f["bones"]), "meshes": f["meshes"],
                                "display_mask_materials": sorted({x for x in f["materials"] if re.match(r"#\d+#", x)})}
for m, base in COUNTERPART.items():
    extra = sorted(info[m]["_bones"] - info[base]["_bones"])
    info[m]["bones_not_in_" + base] = {"count": len(extra), "names": extra[:40]}
    info[m]["bones_shared_with_" + base] = len(info[m]["_bones"] & info[base]["_bones"])
for rec in info.values():
    del rec["_bones"]
same = [m for m in MODELS if info[m]["behavior_script_sha256"] and
        info[m]["behavior_script_sha256"] == info["c7100"]["behavior_script_sha256"]]
for m in same:
    info[m]["behavior_script_same_as"] = [x for x in same if x != m]

# ---- map placements
def part_name_utf16(m):
    """Bytes regex for a UTF-16LE part name such as c7100_0000."""
    return re.compile(b"".join(re.escape(ch.encode("utf-16-le")) for ch in m + "_") + b"(?:[0-9]\x00){4}")


placed = {m: [] for m in MODELS}
for f in sorted((GAME / "map/mapstudio").glob("*.msb.dcx")):
    b = read_dcx(f)
    for m in MODELS:
        n = len(set(part_name_utf16(m).findall(b)))
        if n:
            placed[m].append(f"{f.name.split('.')[0]} ({n} parts)")

# ---- cutscenes and the events that play them
# A cutscene uses a model when its .mqb (cutscene layout) names a part <id>_NNNN, or when one of its animation
# tracks (.hkx) is for <id>_NNNN; the latter alone is recorded as "animation track only".
in_cut = {m: [] for m in MODELS}
for f in sorted((GAME / "cutscene").glob("*.cutscenebnd.dcx")):
    files = bnd_files(read_dcx(f))
    mqb = b"".join(d for n, d in files.items() if n.endswith(".mqb"))
    hkx = b"".join(d for n, d in files.items() if n.endswith(".hkx"))
    for m in MODELS:
        if part_name_utf16(m).search(mqb):
            in_cut[m].append((f.name.split(".")[0], "layout"))
        elif re.search(m.encode() + rb"_[0-9]{4}\x00", hkx):
            in_cut[m].append((f.name.split(".")[0], "animation track only"))
cut_ids = {int(c[1:3] + c[4:6] + c[7:11]): c for cs in in_cut.values() for c, _ in cs}
plays = {c: [] for c in cut_ids.values()}
tmp = out_path.with_suffix(".emevd.tmp")
for f in sorted((GAME / "event").glob("*.emevd.dcx")):
    tmp.write_bytes(read_dcx(f))
    for ev in emevd.load(str(tmp)):
        for x in ev["instrs"]:
            if x["bank"] == 2002 and x["args"] and x["args"][0] in cut_ids:
                key = f"{f.name.split('.')[0]}:{ev['id']}"
                if key not in plays[cut_ids[x["args"][0]]]:
                    plays[cut_ids[x["args"][0]]].append(key)
tmp.unlink()

for m, rec in info.items():
    rec["placed_in_maps"] = placed[m]
    rec["cutscenes"] = [{"cutscene": c, "reference": how, "played_by_events": plays[c]} for c, how in in_cut[m]]

json.dump({"status": "roles confirmed by the project owner on 2026-10-12 (models viewed in DS Anim Studio)",
           "ruleset": "vanilla", "game_version": "1.06", "models": list(info.values())},
          open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.stdout.reconfigure(encoding="utf-8")
for m, rec in info.items():
    s = rec.get("model_summary", {})
    print(m, "| TAE", rec.get("tae_entries"), "anims", rec.get("animations"), "| bones", s.get("bones"),
          "| maps", rec["placed_in_maps"], "| cutscenes", [(c["cutscene"], c["played_by_events"], c["reference"]) for c in rec["cutscenes"]])
