"""Extract one file (by name suffix) from a DCX-compressed BND4 to an output path.

Usage: python -I bnd_extract.py <file.anibnd.dcx> <name_suffix> <out_path>
"""
import struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bnd_names import read_dcx

b = read_dcx(sys.argv[1])
count = struct.unpack_from("<I", b, 0x0C)[0]
entry_size = struct.unpack_from("<Q", b, 0x20)[0]
for i in range(count):
    off = 0x40 + i * entry_size
    size = struct.unpack_from("<Q", b, off + 0x08)[0]
    data_off = struct.unpack_from("<I", b, off + 0x18)[0]
    name_off = struct.unpack_from("<I", b, off + 0x20)[0]
    end = name_off
    while b[end:end + 2] != b"\x00\x00":
        end += 2
    name = b[name_off:end].decode("utf-16-le")
    if name.endswith(sys.argv[2]):
        open(sys.argv[3], "wb").write(b[data_off:data_off + size])
        print(name, size)
