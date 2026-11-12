import struct
import zlib
from pathlib import Path

SIZES = [16, 32, 48, 64, 128, 256]
BG, FG, CLEAR = (47, 111, 178, 255), (255, 255, 255, 255), (0, 0, 0, 0)
BARS = [(0.18, 0.34, 0.52), (0.42, 0.58, 0.36), (0.66, 0.82, 0.22)]  # (x début, x fin, haut), base à 0.78


def _inside_rounded(x, y, size, radius):
    cx = min(max(x, radius), size - radius)
    cy = min(max(y, radius), size - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def _pixel(x, y, size):
    if not _inside_rounded(x + 0.5, y + 0.5, size, size * 0.18):
        return CLEAR
    fx, fy = (x + 0.5) / size, (y + 0.5) / size
    if 0.80 <= fy <= 0.84 and 0.14 <= fx <= 0.86:
        return FG
    if any(x0 <= fx <= x1 and top <= fy <= 0.78 for x0, x1, top in BARS):
        return FG
    return BG


def _png(size):
    raw = b"".join(
        b"\x00" + b"".join(bytes(_pixel(x, y, size)) for x in range(size)) for y in range(size)
    )

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def build_ico(path):
    images = [_png(s) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for size, data in zip(SIZES, images):
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    Path(path).write_bytes(header + entries + b"".join(images))


if __name__ == "__main__":
    build_ico("assets/app.ico")
    print(f"assets\\app.ico créé ({len(SIZES)} tailles)")