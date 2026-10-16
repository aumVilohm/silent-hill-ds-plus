#!/usr/bin/env python3
"""Draw the Ports list picture for Silent Hill DS+: original pixel art made here from
code (a foggy town, the title in a plain 5x7 pixel font, a DS+ badge). No Konami
artwork, logo or cover is used, so the picture can ship with the port.

Writes a 60x60 design scaled 6x (nearest neighbour) to 360x360 PNG."""
import argparse
from pathlib import Path
import struct
import zlib

W = H = 60
SCALE = 6

FONT = {
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'I': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'N': ['#...#', '##..#', '#.#.#', '#.#.#', '#..##', '#...#', '#...#'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
    '+': ['.....', '..#..', '..#..', '#####', '..#..', '..#..', '.....'],
}
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dithered(x, y, top, bottom, t, levels=7):
    """Gradient quantised to a few shades, with ordered dithering between them."""
    v = t * (levels - 1)
    base = int(v)
    if (v - base) * 16 > BAYER[y % 4][x % 4] + 0.5:
        base += 1
    return mix(top, bottom, min(base, levels - 1) / (levels - 1))


def draw():
    px = [[(0, 0, 0)] * W for _ in range(H)]

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                put(x, y, c)

    horizon = 44
    sky_top, fog = hexrgb('#16181c'), hexrgb('#a9adb2')
    ground_far, ground_near = hexrgb('#8f9398'), hexrgb('#34373c')
    for y in range(H):
        for x in range(W):
            if y < horizon:
                px[y][x] = dithered(x, y, sky_top, fog, (y / horizon) ** 1.6)
            else:
                px[y][x] = dithered(x, y, ground_far, ground_near, (y - horizon) / (H - 1 - horizon))

    # The road into the fog, darker as it comes closer, with a broken centre line.
    for y in range(horizon, H):
        t = (y - horizon) / (H - 1 - horizon)
        half = 1 + t * 13
        for x in range(round(30 - half), round(30 + half)):
            put(x, y, dithered(x, y, hexrgb('#7d8186'), hexrgb('#24262a'), t, 5))
        if (y - horizon) % 5 in (2, 3) and t > 0.15:
            put(29, y, hexrgb('#c9c7bd'))
            put(30, y, hexrgb('#c9c7bd'))

    # Distant rooftops, nearly lost in the fog.
    far = hexrgb('#979ba0')
    for x0, w, h in ((0, 7, 3), (8, 5, 5), (19, 9, 4), (33, 6, 6), (40, 8, 3), (50, 10, 5)):
        rect(x0, horizon - h, x0 + w - 1, horizon - 1, far)
        for i in range(w // 2 + 1):
            rect(x0 + i, horizon - h - i, x0 + w - 1 - i, horizon - h - i, far)

    # A church with a steeple (left) and a utility pole with sagging wires (right).
    mid = hexrgb('#5f646b')
    rect(4, 35, 15, horizon - 1, mid)
    for i in range(7):
        rect(4 + i, 35 - i, 15 - i, 35 - i, mid)
    rect(12, 24, 14, 34, mid)
    for i in range(3):
        put(12 + i, 23 - (1 if i == 1 else 0), mid)
    put(13, 20, mid); put(13, 21, mid); put(12, 20, mid); put(14, 20, mid); put(13, 19, mid)
    for y in range(37, 41):
        put(7, y, hexrgb('#3d4046')); put(8, y, hexrgb('#3d4046'))
    put(11, 29, hexrgb('#c0392b'))  # one lit window in the steeple
    pole = hexrgb('#3b3e44')
    rect(48, 22, 48, horizon - 1, pole)
    rect(45, 24, 51, 24, pole)
    for x in range(17, 48):
        sag = round(((x - 32) / 15.5) ** 2 * 3)
        put(x, 27 - sag + 3, hexrgb('#4a4e55'))

    # Falling ash.
    ash = hexrgb('#d8d8d4')
    seed = 7
    for _ in range(38):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        x, y = seed % W, (seed >> 8) % horizon
        if y > 18:
            put(x, y, ash)

    # Title: plain 5x7 pixel letters with a dark shadow.
    red, shadow = hexrgb('#c22a1f'), hexrgb('#050506')

    def text(s, x0, y0, colour):
        for k, ch in enumerate(s):
            for r, row in enumerate(FONT[ch]):
                for c, bit in enumerate(row):
                    if bit == '#':
                        put(x0 + k * 6 + c + 1, y0 + r + 1, shadow)
        for k, ch in enumerate(s):
            for r, row in enumerate(FONT[ch]):
                for c, bit in enumerate(row):
                    if bit == '#':
                        put(x0 + k * 6 + c, y0 + r, colour)

    text('SILENT', (W - 35) // 2, 3, red)
    text('HILL', (W - 23) // 2, 12, red)

    # DS+ badge.
    rect(37, 48, 57, 58, hexrgb('#e4e4e0'))
    rect(38, 49, 56, 57, hexrgb('#7e1a13'))
    text('DS+', 39, 50, hexrgb('#f2f2ee'))
    return px


def png(rows, path):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b''.join(b'\0' + bytes(v for p in row for v in p) for row in rows)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', len(rows[0]), len(rows), 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'port/SilentHill.box.png')
args = parser.parse_args()
small = draw()
big = [[p for p in row for _ in range(SCALE)] for row in small for _ in range(SCALE)]
png(big, args.out)
print(args.out, f'{W * SCALE}x{H * SCALE}')
