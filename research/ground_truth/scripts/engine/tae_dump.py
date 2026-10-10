"""Dump every animation entry and event of a Sekiro (TAE version 0x1000D) .tae file to JSON.

Usage: python -I tae_dump.py <file.tae> <TAE.Template.SDT.xml> <out.json>

Event names and parameter layouts come from DS Anim Studio's template (bank 14, Characters).
"""
import json
import struct
import sys
import xml.etree.ElementTree as ET

SIZES = {"b": 1, "u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4, "f32": 4}
FMT = {"b": "?", "u8": "B", "s8": "b", "u16": "H", "s16": "h", "u32": "I", "s32": "i", "f32": "f"}


def load_template(path, bank_id="14"):
    root = ET.parse(path).getroot()
    bank = next(b for b in root.iter("bank") if b.get("id") == bank_id)
    events = {}
    for ev in bank.iter("event"):
        fields = []
        for f in ev:
            if f.tag == "aob":
                fields.append(("aob", f.get("name"), int(f.get("length"))))
            elif f.tag in SIZES:
                fields.append((f.tag, f.get("name"), None))
        events[int(ev.get("id"))] = (ev.get("name") or f"Event{ev.get('id')}", fields)
    return events


def anim_name(aid):
    return f"a{aid // 1000000:03d}_{aid % 1000000:06d}"


def parse(tae_path, template):
    b = open(tae_path, "rb").read()
    assert b[:4] == b"TAE ", "not a TAE file"
    version = struct.unpack_from("<I", b, 0x08)[0]
    assert version == 0x1000D, f"expected Sekiro TAE version 0x1000D, got {version:#x}"
    u32 = lambda o: struct.unpack_from("<I", b, o)[0]
    u64 = lambda o: struct.unpack_from("<Q", b, o)[0]
    f32 = lambda o: struct.unpack_from("<f", b, o)[0]

    tae_id, count, table = u32(0x50), u32(0x54), u64(0x58)
    anims = []
    for i in range(count):
        aid, off = struct.unpack_from("<QQ", b, table + 16 * i)
        ev_hdr, _ev_grp, _times, mini = struct.unpack_from("<4Q", b, off)
        ev_count = u32(off + 0x20)

        mini_type = u64(mini)
        entry = {"id": anim_name(aid), "id_int": aid}
        if mini_type == 0:  # Standard: plays its own hkx, or another one's if ImportsHKX
            loop, imports_hkx = b[mini + 0x18], b[mini + 0x19]
            src = struct.unpack_from("<i", b, mini + 0x1C)[0]
            entry["kind"] = "standard"
            entry["loop"] = bool(loop)
            entry["hkx"] = anim_name(src) if imports_hkx and src >= 0 else entry["id"]
        elif mini_type == 1:  # ImportOtherAnim: takes both events and hkx from another entry
            entry["kind"] = "import_other_anim"
            entry["imports_from"] = anim_name(struct.unpack_from("<i", b, mini + 0x18)[0])
        else:
            raise ValueError(f"{entry['id']}: unknown mini header type {mini_type}")

        events = []
        for k in range(ev_count):
            s_off, e_off, d_off = struct.unpack_from("<3Q", b, ev_hdr + 24 * k)
            etype, p_off = u64(d_off), u64(d_off + 8)
            name, fields = template.get(etype, (f"Unknown{etype}", []))
            params, p = {}, p_off
            for ftype, fname, length in fields:
                if ftype == "aob":
                    if fname:
                        params[fname] = b[p:p + length].hex(" ")
                    p += length
                    continue
                val = struct.unpack_from("<" + FMT[ftype], b, p)[0]
                if fname:
                    params[fname] = round(val, 4) if ftype == "f32" else val
                p += SIZES[ftype]
            start, end = f32(s_off), f32(e_off)
            events.append({
                "type": etype, "name": name,
                "start_s": round(start, 4), "end_s": round(end, 4),
                "start_frame_30": round(start * 30, 2), "end_frame_30": round(end * 30, 2),
                "params": params,
            })
        entry["events"] = events
        anims.append(entry)
    return {"tae_id": tae_id, "animation_count": count, "animations": anims}


if __name__ == "__main__":
    tae_path, template_path, out_path = sys.argv[1:4]
    data = parse(tae_path, load_template(template_path))
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"TAE id {data['tae_id']}, {data['animation_count']} entries -> {out_path}")
