"""Minimal reader for Sekiro EMEVD (version 0xCD, 64-bit): events, instructions and their raw int32 args.

Usage: python -I emevd.py <file.emevd> <value> [<value> ...]
Prints every event containing an instruction whose arguments include one of the values (as int32),
with all its instructions as bank[id] followed by the args read as int32.
"""
import struct
import sys


def load(path):
    b = open(path, "rb").read()
    assert b[:4] == b"EVD\0" and struct.unpack_from("<I", b, 8)[0] == 0xCD
    q = lambda o: struct.unpack_from("<q", b, o)[0]
    ev_n, ev_o, in_n, in_o = q(0x10), q(0x18), q(0x20), q(0x28)
    par_n, par_o = q(0x50), q(0x58)
    args_o = q(0x78)
    events = []
    for i in range(ev_n):
        eid, icount, ioff, pcount, poff, rest = struct.unpack_from("<qqqqqi", b, ev_o + 0x30 * i)
        instrs = []
        for j in range(icount):
            o = in_o + ioff + 0x20 * j
            bank, iid, alen, aoff, loff = struct.unpack_from("<iiqqq", b, o)
            raw = b[args_o + aoff: args_o + aoff + alen]
            ints = list(struct.unpack_from(f"<{alen // 4}i", raw)) if alen % 4 == 0 else []
            instrs.append({"bank": bank, "id": iid, "args": ints, "raw": raw})
        params = []
        for j in range(pcount):
            pi, dst, src, n = struct.unpack_from("<qqqq", b, par_o + poff + 0x20 * j)
            params.append((pi, dst, src, n))
        events.append({"id": eid, "rest": rest, "instrs": instrs, "params": params})
    return events


if __name__ == "__main__":
    evs = load(sys.argv[1])
    want = {int(v) for v in sys.argv[2:]}
    print(len(evs), "events")
    for e in evs:
        if any(want & set(x["args"]) for x in e["instrs"]):
            print(f"\n=== event {e['id']} (rest {e['rest']}), params {e['params']}")
            for k, x in enumerate(e["instrs"]):
                mark = "  <==" if want & set(x["args"]) else ""
                print(f"  [{k:2d}] {x['bank']}[{x['id']:02d}] {x['args']}{mark}")
