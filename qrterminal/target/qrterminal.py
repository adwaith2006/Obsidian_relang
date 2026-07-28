#!/usr/bin/env python3
"""
QRTerminal - Terminal QR Code Generator in Python 3.
Ported from Go (rsc.io/qr and github.com/mdp/qrterminal/v3).
"""

import sys
import io
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

# -----------------------------------------------------------------------------
# Constants & Enums matching Go source
# -----------------------------------------------------------------------------

WHITE = "\033[47m  \033[0m"
BLACK = "\033[40m  \033[0m"

BLACK_WHITE = "▄"
BLACK_BLACK = " "
WHITE_BLACK = "▀"
WHITE_WHITE = "█"

# Error Correction Levels matching Go qr.Level
L = "L"
M = "M"
Q = "Q"
H = "H"

QUIET_ZONE = 4

SIXEL_BEGIN = "\x1bPq\n#0;2;0;0;0#1;2;100;100;100\n"
SIXEL_END = "\x1b\\"
SIXEL_BLOCK_SIZE = 12

# Level map string -> numeric index
LEVEL_MAP = {
    'L': 0, 'l': 0, 0: 0,
    'M': 1, 'm': 1, 1: 1,
    'Q': 2, 'q': 2, 2: 2,
    'H': 3, 'h': 3, 3: 3,
}

# -----------------------------------------------------------------------------
# Configuration Data Class
# -----------------------------------------------------------------------------

@dataclass
class Config:
    level: Any = L
    writer: Any = None
    half_blocks: bool = False
    black_char: str = ""
    black_white_char: str = ""
    white_char: str = ""
    white_black_char: str = ""
    quiet_zone: int = QUIET_ZONE
    with_sixel: bool = False

    def __post_init__(self):
        if self.writer is None:
            self.writer = sys.stdout

# -----------------------------------------------------------------------------
# Galois Field GF(256) & Reed-Solomon Encoder matching Go rsc.io/qr
# -----------------------------------------------------------------------------

class GF256Field:
    def __init__(self, poly=0x11d, alpha=2):
        self.log = [0] * 256
        self.exp = [0] * 510
        x = 1
        for i in range(255):
            self.exp[i] = x
            self.exp[i + 255] = x
            self.log[x] = i
            z = 0
            px = x
            y = alpha
            while px > 0:
                if px & 1:
                    z ^= y
                px >>= 1
                y <<= 1
                if y & 0x100:
                    y ^= poly
            x = z
        self.log[0] = 255

    def mul(self, x: int, y: int) -> int:
        if x == 0 or y == 0:
            return 0
        return self.exp[self.log[x] + self.log[y]]

    def gen(self, e: int):
        p = [0] * (e + 1)
        p[e] = 1
        for i in range(e):
            c = self.exp[i]
            for j in range(e):
                p[j] = self.mul(p[j], c) ^ p[j + 1]
            p[e] = self.mul(p[e], c)

        lgen = [0] * (e + 1)
        for i, c in enumerate(p):
            if c == 0:
                lgen[i] = 255
            else:
                lgen[i] = self.log[c]
        return p, lgen

    def ecc(self, data: List[int], e: int) -> List[int]:
        gen, lgen = self.gen(e)
        lgen_sub = lgen[1:]
        p = list(data) + [0] * e
        for i in range(len(data)):
            c = p[i]
            if c == 0:
                continue
            q_offset = i + 1
            exp_offset = self.log[c]
            for j, lg in enumerate(lgen_sub):
                if lg != 255:
                    p[q_offset + j] ^= self.exp[exp_offset + lg]
        return p[len(data):]

_field = GF256Field()

# Version table capacity (total_bytes, level_specs: [L, M, Q, H] of (nblock, check_bytes))
VTAB = {
    1: (26, [(1, 7), (1, 10), (1, 13), (1, 17)]),
    2: (44, [(1, 10), (1, 16), (1, 22), (1, 28)]),
    3: (70, [(1, 15), (1, 26), (2, 18), (2, 22)]),
    4: (100, [(1, 20), (2, 18), (2, 26), (4, 16)]),
    5: (134, [(1, 26), (2, 24), (4, 18), (4, 22)]),
}

ALIGNMENT_POS = {
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
}

class QRCode:
    def __init__(self, size: int, modules: List[List[bool]]):
        self.Size = size
        self._modules = modules

    def Black(self, x: int, y: int) -> bool:
        if 0 <= x < self.Size and 0 <= y < self.Size:
            return self._modules[y][x]
        return False

def _encode_qr_matrix(text: str, level_val: int) -> QRCode:
    data_bytes = text.encode('utf-8')
    data_len = len(data_bytes)

    # Version selection matching rsc.io/qr
    version = 1
    while version <= 5:
        total_b, lspecs = VTAB[version]
        nblock, check_cw = lspecs[level_val]
        data_cw = total_b - nblock * check_cw
        req_bits = 4 + 8 + (data_len * 8)
        if req_bits <= data_cw * 8:
            break
        version += 1

    if version > 5:
        version = 5

    total_b, lspecs = VTAB[version]
    nblock, check_cw = lspecs[level_val]
    data_cw = total_b - nblock * check_cw

    # Bitstream packing
    bits = []
    def put_bits(val, count):
        for i in range(count - 1, -1, -1):
            bits.append((val >> i) & 1)

    put_bits(4, 4)         # 8-bit byte mode
    put_bits(data_len, 8)  # len
    for b in data_bytes:
        put_bits(b, 8)

    pad_needed = data_cw * 8 - len(bits)
    if pad_needed > 0:
        put_bits(0, min(4, pad_needed))

    while len(bits) % 8 != 0:
        bits.append(0)

    pad_bytes = [0xEC, 0x11]
    pad_idx = 0
    while len(bits) < data_cw * 8:
        put_bits(pad_bytes[pad_idx], 8)
        pad_idx = (pad_idx + 1) % 2

    # Codewords
    codewords = []
    for i in range(0, len(bits), 8):
        b_val = 0
        for b in range(8):
            b_val = (b_val << 1) | bits[i + b]
        codewords.append(b_val)

    # RS Blocks & interleaving
    nde = (total_b - check_cw * nblock) // nblock
    extra = (total_b - check_cw * nblock) % nblock

    data_list = []
    check_list = []
    offset = 0
    for i in range(nblock):
        nd = nde + (1 if i >= nblock - extra else 0)
        blk = codewords[offset:offset + nd]
        offset += nd
        data_list.append(blk)
        check_list.append(_field.ecc(blk, check_cw))

    final_cw = []
    for i in range(nde + 1):
        for blk in data_list:
            if i < len(blk):
                final_cw.append(blk[i])
    for i in range(check_cw):
        for chk in check_list:
            if i < len(chk):
                final_cw.append(chk[i])

    all_bits = []
    for cw in final_cw:
        for b in range(7, -1, -1):
            all_bits.append((cw >> b) & 1 == 1)

    all_bits.extend([False] * 7)

    siz = 17 + version * 4
    matrix = [[False] * siz for _ in range(siz)]
    reserved = [[False] * siz for _ in range(siz)]

    def set_res(r, c, val):
        matrix[r][c] = val
        reserved[r][c] = True

    # 1. Timing markers
    for i in range(siz):
        val = (i % 2 == 0)
        set_res(6, i, val)
        set_res(i, 6, val)

    # 2. Finder boxes
    finders = [(0, 0), (0, siz - 7), (siz - 7, 0)]
    for fr, fc in finders:
        for r in range(7):
            for c in range(7):
                is_b = (r == 0 or r == 6 or c == 0 or c == 6 or (2 <= r <= 4 and 2 <= c <= 4))
                set_res(fr + r, fc + c, is_b)
        for r in range(-1, 8):
            for c in range(-1, 8):
                if 0 <= fr + r < siz and 0 <= fc + c < siz:
                    if not reserved[fr + r][fc + c]:
                        set_res(fr + r, fc + c, False)

    # 3. Alignment boxes
    if version in ALIGNMENT_POS:
        align_centers = ALIGNMENT_POS[version]
        for r_center in align_centers:
            for c_center in align_centers:
                if (r_center < 7 and c_center < 7) or (r_center < 7 and c_center >= siz - 7) or (r_center >= siz - 7 and c_center < 7):
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        is_b = (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0))
                        set_res(r_center + dr, c_center + dc, is_b)

    # 4. Format info reserved
    for i in range(9):
        if not reserved[8][i]: set_res(8, i, False)
        if not reserved[i][8]: set_res(i, 8, False)
    for i in range(siz - 8, siz):
        if not reserved[8][i]: set_res(8, i, False)
        if not reserved[i][8]: set_res(i, 8, False)

    # Lonely black pixel
    set_res(siz - 8, 8, True)

    # 5. Place data bits (sweep x from siz down to 0)
    src = list(all_bits)
    x = siz
    while x > 0:
        for y in range(siz - 1, -1, -1):
            if not reserved[y][x - 1]:
                matrix[y][x - 1] = src.pop(0) if src else False
            if not reserved[y][x - 2]:
                matrix[y][x - 2] = src.pop(0) if src else False
        x -= 2
        if x == 7:
            x -= 1
        for y in range(siz):
            if not reserved[y][x - 1]:
                matrix[y][x - 1] = src.pop(0) if src else False
            if not reserved[y][x - 2]:
                matrix[y][x - 2] = src.pop(0) if src else False
        x -= 2

    # 6. Mask 0: (y + x) % 2 == 0 matching rsc.io/qr
    mask = 0
    for r in range(siz):
        for c in range(siz):
            if not reserved[r][c]:
                if (r + c) % 2 == 0:
                    matrix[r][c] = not matrix[r][c]

    # 7. Format Info (level_val ^ 1)
    fb = (level_val ^ 1) << 13
    fb |= mask << 10
    rem = fb
    format_poly = 0x537
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= format_poly << (i - 10)
    fb |= rem
    invert = 0x5412

    for i in range(15):
        bit_val = (fb >> i) & 1
        inv_val = (invert >> i) & 1
        final_val = (bit_val ^ inv_val) == 1

        if i < 6:
            matrix[i][8] = final_val
        elif i < 8:
            matrix[i + 1][8] = final_val
        elif i < 9:
            matrix[8][7] = final_val
        else:
            matrix[8][14 - i] = final_val

        if i < 8:
            matrix[8][siz - 1 - i] = final_val
        else:
            matrix[siz - 1 - (14 - i)][8] = final_val

    return QRCode(siz, matrix)

# -----------------------------------------------------------------------------
# Terminal Renderer Functions matching Go API
# -----------------------------------------------------------------------------

def string_repeat(s: str, count: int) -> str:
    if count <= 0:
        return ""
    return s * count

def _write_bytes(w: Any, s: str):
    if hasattr(w, "write"):
        if isinstance(s, str):
            w.write(s)
        else:
            w.write(str(s))

def is_sixel_supported(w: Any) -> bool:
    if w != sys.stdout:
        return False
    if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
        return False
    return False

def _write_full_blocks(c: Config, code: QRCode):
    w = c.writer
    white = c.white_char
    black = c.black_char

    _write_bytes(w, string_repeat(string_repeat(white, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone))

    for i in range(code.Size):
        _write_bytes(w, string_repeat(white, c.quiet_zone))
        for j in range(code.Size):
            if code.Black(j, i):
                _write_bytes(w, black)
            else:
                _write_bytes(w, white)
        _write_bytes(w, string_repeat(white, c.quiet_zone - 1) + "\n")

    _write_bytes(w, string_repeat(string_repeat(white, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone - 1))

def _write_half_blocks(c: Config, code: QRCode):
    w = c.writer
    ww = c.white_char
    bb = c.black_char
    wb = c.white_black_char
    bw = c.black_white_char

    if c.quiet_zone % 2 != 0:
        _write_bytes(w, string_repeat(bw, code.Size + c.quiet_zone * 2) + "\n")
        _write_bytes(w, string_repeat(string_repeat(ww, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone // 2))
    else:
        _write_bytes(w, string_repeat(string_repeat(ww, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone // 2))

    for i in range(0, code.Size, 2):
        _write_bytes(w, string_repeat(ww, c.quiet_zone))
        for j in range(code.Size):
            next_black = False
            if i + 1 < code.Size:
                next_black = code.Black(j, i + 1)
            curr_black = code.Black(j, i)

            if curr_black and next_black:
                _write_bytes(w, bb)
            elif curr_black and not next_black:
                _write_bytes(w, bw)
            elif not curr_black and not next_black:
                _write_bytes(w, ww)
            else:
                _write_bytes(w, wb)
        _write_bytes(w, string_repeat(ww, c.quiet_zone - 1) + "\n")

    if c.quiet_zone % 2 == 0:
        _write_bytes(w, string_repeat(string_repeat(ww, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone // 2 - 1))
        _write_bytes(w, string_repeat(wb, code.Size + c.quiet_zone * 2) + "\n")
    else:
        _write_bytes(w, string_repeat(string_repeat(ww, code.Size + c.quiet_zone * 2) + "\n", c.quiet_zone // 2))

def _write_sixel(c: Config, code: QRCode):
    w = c.writer
    size = SIXEL_BLOCK_SIZE
    if code.Size > 50:
        size //= 2
    line = size // 6

    _write_bytes(w, SIXEL_BEGIN)
    _write_bytes(w, string_repeat(f"#1!{size * (code.Size + c.quiet_zone * 2)}~-\n", c.quiet_zone * line))

    for i in range(code.Size):
        flag = -1
        repeat = 0
        content = []
        if c.quiet_zone > 0:
            content.append(f"#1!{size * c.quiet_zone}~")

        for j in range(code.Size):
            if code.Black(j, i):
                if flag == 1:
                    content.append(f"#1!{size * repeat}~")
                    repeat = 0
                flag = 0
                repeat += 1
            else:
                if flag == 0:
                    content.append(f"#0!{size * repeat}~")
                    repeat = 0
                flag = 1
                repeat += 1

        if repeat > 0:
            content.append(f"#{flag}!{size * repeat}~")
        if c.quiet_zone > 1:
            content.append(f"#1!{size * (c.quiet_zone - 1)}~")

        content.append("-\n")
        line_str = "".join(content)
        for _ in range(line):
            _write_bytes(w, line_str)

    _write_bytes(w, string_repeat(f"#1!{size * (code.Size + c.quiet_zone * 2)}~-\n", (c.quiet_zone - 1) * line))
    if c.quiet_zone > 1:
        _write_bytes(w, f"#1!{size * (code.Size + c.quiet_zone * 2)}~-")
    _write_bytes(w, SIXEL_END)

# -----------------------------------------------------------------------------
# Public API Functions matching Go qrterminal
# -----------------------------------------------------------------------------

def generate_with_config(text: str, config: Config):
    if config.quiet_zone < 1:
        config.quiet_zone = 1

    level_val = LEVEL_MAP.get(config.level, 0)
    code = _encode_qr_matrix(text, level_val)

    if not config.black_char:
        config.black_char = BLACK_BLACK
    if not config.white_black_char:
        config.white_black_char = WHITE_BLACK
    if not config.white_char:
        config.white_char = WHITE_WHITE
    if not config.black_white_char:
        config.black_white_char = BLACK_WHITE

    if config.half_blocks:
        _write_half_blocks(config, code)
    elif config.with_sixel:
        _write_sixel(config, code)
    else:
        _write_full_blocks(config, code)

def generate(text: str, level: Any = L, writer: Any = sys.stdout):
    config = Config(
        level=level,
        writer=writer,
        black_char=BLACK,
        white_char=WHITE,
        quiet_zone=QUIET_ZONE,
    )
    config.with_sixel = is_sixel_supported(writer)
    generate_with_config(text, config)

def generate_half_block(text: str, level: Any = L, writer: Any = sys.stdout):
    config = Config(
        level=level,
        writer=writer,
        half_blocks=True,
        black_char=BLACK_BLACK,
        white_black_char=WHITE_BLACK,
        white_char=WHITE_WHITE,
        black_white_char=BLACK_WHITE,
        quiet_zone=QUIET_ZONE,
    )
    generate_with_config(text, config)

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "https://example.com"
    generate_half_block(text, L)