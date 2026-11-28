"""Minimal reader for Havok TAG0 tagfiles (local research: Sekiro behavior graphs; outputs are game-derived, never commit).

Usage: python -I tag0.py <file.hkx> sections | types <regex> | items <TypeName> [field ...]
Sections: 4-byte big-endian size (low 30 bits, header included) + 4-char tag; TAG0, TYPE and INDX hold subsections.
"""
import re
import struct
import sys

CONTAINERS = {b"TAG0", b"TYPE", b"INDX"}


def sections(b, start=0, end=None, depth=0):
    end = len(b) if end is None else end
    i = start
    while i + 8 <= end:
        v = struct.unpack(">I", b[i:i + 4])[0]
        size, tag = v & 0x3FFFFFFF, b[i + 4:i + 8]
        yield depth, tag, i + 8, i + size
        if tag in CONTAINERS:
            yield from sections(b, i + 8, i + size, depth + 1)
        if size <= 0:
            break
        i += size


class R:
    def __init__(self, b, i, end):
        self.b, self.i, self.end = b, i, end

    def u8(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def varint(self):
        b0 = self.u8()
        if b0 & 0x80 == 0:
            return b0
        if b0 & 0xC0 == 0x80:
            return ((b0 & 0x3F) << 8) | self.u8()
        if b0 & 0xE0 == 0xC0:
            return ((b0 & 0x1F) << 16) | (self.u8() << 8) | self.u8()
        if b0 & 0xF8 == 0xE0:
            return ((b0 & 0x07) << 24) | (self.u8() << 16) | (self.u8() << 8) | self.u8()
        if b0 & 0xF8 == 0xE8:
            v = ((b0 & 0x07) << 32) | int.from_bytes(self.b[self.i:self.i + 4], "big")
            self.i += 4
            return v
        raise ValueError(f"varint 0x{b0:02X} at {self.i - 1}")


def strings(b, s, e):
    return [x.decode("latin-1") for x in b[s:e].split(b"\0")]


def load(path):
    b = open(path, "rb").read()
    sec = {tag: (s, e) for _, tag, s, e in sections(b)}
    tst = strings(b, *sec[b"TSTR"])
    fst = strings(b, *sec[b"FSTR"])
    # type names: count, then per type: name index, template count, templates (name index, value)
    r = R(b, *sec[b"TNA1"])
    n = r.varint()
    names = {0: None}
    for t in range(1, n):
        names[t] = tst[r.varint()]
        for _ in range(r.varint()):
            r.varint()
            r.varint()
    # type bodies
    body = {}
    r = R(b, *sec[b"TBDY"])
    while r.i < r.end:
        t = r.varint()
        if t == 0:
            continue
        info = {"parent": r.varint()}
        flags = r.varint()
        if flags & 0x1:
            info["format"] = r.varint()
        if flags & 0x2:
            info["subtype"] = r.varint()
        if flags & 0x4:
            info["version"] = r.varint()
        if flags & 0x8:
            info["size"], info["align"] = r.varint(), r.varint()
        if flags & 0x10:
            info["abstract"] = r.varint()
        if flags & 0x20:
            info["members"] = []
            for _ in range(r.varint()):
                info["members"].append((fst[r.varint()], r.varint(), r.varint(), r.varint()))   # name, flags, offset, type
        if flags & 0x40:
            for _ in range(r.varint()):
                r.varint()
                r.varint()
        if flags & 0x80:
            info["attr"] = r.varint()
        body[t] = info
    # items: (type and flags, offset in DATA, count)
    s, e = sec[b"ITEM"]
    items = [struct.unpack("<III", b[i:i + 12]) for i in range(s, e, 12)]
    data0 = sec[b"DATA"][0]
    return b, sec, names, body, items, data0


def all_members(body, t):
    out = []
    while t:
        out = body.get(t, {}).get("members", []) + out
        t = body.get(t, {}).get("parent", 0)
    return out


if __name__ == "__main__":
    b, sec, names, body, items, data0 = load(sys.argv[1])
    cmd = sys.argv[2]
    if cmd == "sections":
        for d, tag, s, e in sections(b):
            print("  " * d + f"{tag.decode('latin-1')} {e - s} bytes")
        print(len(names) - 1, "types,", len(items), "items")
    elif cmd == "types":
        for t, nm in names.items():
            if nm and re.search(sys.argv[3], nm):
                print(t, nm, {k: v for k, v in body.get(t, {}).items() if k != "members"})
                for m in all_members(body, t):
                    print("    ", m[0], "flags", m[1], "offset", m[2], "type", names.get(m[3]))


def item_string(b, items, data0, ref):
    if ref <= 0 or ref >= len(items):
        return None
    _, off, cnt = items[ref]
    return b[data0 + off:data0 + off + cnt].split(b"\0")[0].decode("latin-1")


def clip_nodes(path, pattern):
    b, sec, names, body, items, data0 = load(path)
    tid = next(t for t, n in names.items() if n == "hkbClipGenerator")
    out = []
    for k, (tf, off, cnt) in enumerate(items):
        if tf & 0xFFFFFF != tid:
            continue
        for j in range(cnt):
            o = data0 + off + j * body[tid]["size"]
            name = item_string(b, items, data0, struct.unpack_from("<Q", b, o + 72)[0])
            anim = item_string(b, items, data0, struct.unpack_from("<Q", b, o + 152)[0])
            if not re.search(pattern, f"{name} {anim}"):
                continue
            crop0, crop1, start, speed, enforced, uctf = struct.unpack_from("<6f", b, o + 172)
            mode, flags = b[o + 196], struct.unpack_from("<b", b, o + 197)[0]
            out.append(dict(name=name, anim=anim, cropStart=crop0, cropEnd=crop1, startTime=start, speed=speed,
                            enforcedDuration=enforced, mode=mode, flags=flags))
    return out


if __name__ == "__main__" and sys.argv[2] == "clips":
    for c in clip_nodes(sys.argv[1], sys.argv[3]):
        print(c)
