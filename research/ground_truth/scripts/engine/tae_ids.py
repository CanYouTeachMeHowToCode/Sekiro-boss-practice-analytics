"""List animation entry IDs from a Sekiro TAE file (header at 0x50: count, table offset).

Usage: python -I tae_ids.py <file.tae>
"""
import struct, sys

def tae_ids(path):
    b = open(path, "rb").read()
    assert b[:4] == b"TAE ", b[:4]
    count = struct.unpack_from("<I", b, 0x54)[0]
    table = struct.unpack_from("<Q", b, 0x58)[0]
    ids = [struct.unpack_from("<Q", b, table + 16 * i)[0] for i in range(count)]
    assert ids == sorted(ids), "entry IDs are not sorted; layout assumption is wrong"
    return ids

if __name__ == "__main__":
    for i in tae_ids(sys.argv[1]):
        print(f"a{i // 1000000:03d}_{i % 1000000:06d}")
