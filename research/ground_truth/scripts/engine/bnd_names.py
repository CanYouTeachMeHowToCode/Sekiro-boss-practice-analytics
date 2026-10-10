"""List file names inside a FromSoftware DCX-compressed BND4 (DFLT or KRAK).

Usage: python -I bnd_names.py <file.anibnd.dcx>
KRAK (Oodle) payloads are decompressed with the game's own oo2core_6_win64.dll, loaded read-only from
game_dir in research/ground_truth/local.config.
"""
import configparser
import struct, sys, zlib
from pathlib import Path

LOCAL_CONFIG = Path(__file__).resolve().parents[2] / "local.config"


def oodle_dll():
    cfg = configparser.ConfigParser()
    if not cfg.read(LOCAL_CONFIG, encoding="utf-8"):
        raise SystemExit(f"{LOCAL_CONFIG} not found: copy local.config.example and fill in game_dir")
    return str(Path(cfg["paths"]["game_dir"]) / "oo2core_6_win64.dll")


def oodle_decompress(payload, usize):
    """Decompress with the game's own Oodle library (read-only use)."""
    import ctypes
    lib = ctypes.WinDLL(oodle_dll())
    fn = lib.OodleLZ_Decompress
    fn.restype = ctypes.c_ssize_t
    fn.argtypes = [ctypes.c_char_p, ctypes.c_ssize_t, ctypes.c_char_p, ctypes.c_ssize_t,
                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_ssize_t,
                   ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ssize_t, ctypes.c_int]
    out = ctypes.create_string_buffer(usize)
    n = fn(payload, len(payload), out, usize, 1, 0, 0, None, 0, None, None, None, 0, 3)
    assert n == usize, (n, usize)
    return out.raw


def read_dcx(path):
    data = open(path, "rb").read()
    assert data[:4] == b"DCX\x00", "not DCX"
    comp = data[0x28:0x2C]
    usize, csize = struct.unpack(">II", data[0x1C:0x24])
    payload = data[0x4C:0x4C + csize]
    if comp == b"DFLT":
        out = zlib.decompress(payload)
    elif comp == b"KRAK":
        out = oodle_decompress(payload, usize)
    else:
        raise SystemExit(f"unsupported compression {comp!r}")
    assert len(out) == usize, (len(out), usize)
    return out

def bnd4_names(b):
    assert b[:4] == b"BND4", b[:4]
    count = struct.unpack_from("<I", b, 0x0C)[0]
    header_size = struct.unpack_from("<Q", b, 0x10)[0]
    entry_size = struct.unpack_from("<Q", b, 0x20)[0]
    unicode = b[0x30] == 1
    names = []
    for i in range(count):
        off = 0x40 + i * entry_size
        name_off = struct.unpack_from("<I", b, off + entry_size - 4 if entry_size == 0x24 else off + 0x20)[0]
        if unicode:
            end = name_off
            while b[end:end + 2] != b"\x00\x00":
                end += 2
            names.append(b[name_off:end].decode("utf-16-le"))
        else:
            names.append(b[name_off:b.index(b"\x00", name_off)].decode("shift_jis"))
    return names

if __name__ == "__main__":
    b = read_dcx(sys.argv[1])
    for n in bnd4_names(b):
        print(n)
