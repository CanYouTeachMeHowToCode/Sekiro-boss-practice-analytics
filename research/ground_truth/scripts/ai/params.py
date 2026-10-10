"""Minimal reader for Sekiro PARAM files inside gameparam.parambnd (rows only, no paramdef).

load_bnd takes the decompressed bytes of param/gameparam/gameparam.parambnd.dcx (see scripts/engine/bnd_names.read_dcx).

Rows are (int id, int pad, long dataOffset, long nameOffset) when the 64-bit flag is set; the row size is the
distance between consecutive data offsets.
"""
import struct


def load_bnd(b):
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
        out[b[noff:e].decode("utf-16-le").split("\\")[-1]] = b[doff:doff + size]
    return out


def rows(p):
    """Return {row_id: row_bytes} for one PARAM file."""
    count = struct.unpack_from("<H", p, 0x0A)[0]
    fmt2d = p[0x2D]
    assert fmt2d & 1 or fmt2d & 4, f"unexpected format {fmt2d:#x}"
    start = 0x40
    ents = [struct.unpack_from("<iiqq", p, start + 24 * i) for i in range(count)]
    offs = sorted({e[2] for e in ents})
    size = min(b - a for a, b in zip(offs, offs[1:])) if len(offs) > 1 else None
    return {e[0]: p[e[2]:e[2] + size] for e in ents}, size
