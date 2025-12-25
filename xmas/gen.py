#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, List, Tuple, TypeVar
from PIL import Image
import numpy as np
import random
import sys

DISPLAY_W = 132
DISPLAY_H_TOTAL = 128
DISPLAY_H_SINGLE = 64

ADDR_TOP = 0x3C
ADDR_BOTTOM = 0x3D

# Each output row: (addr, payload_bytes)
I2CRow = Tuple[int, List[int]]

Pixel = Tuple[int, int]
T = TypeVar("T")


# -------------------------
# SH1106 addressing helpers
# -------------------------

def sh1106_set_page_cmd(page: int) -> int:
    return 0xB0 | (page & 0x0F)


def sh1106_set_col_cmds(col: int) -> List[int]:
    col = col & 0xFF
    low = 0x00 | (col & 0x0F)
    high = 0x10 | ((col >> 4) & 0x0F)
    return [low, high]


def emit_ctrl(rows: List[I2CRow], addr: int, page: int, col: int) -> None:
    rows.append((addr, [0x00, sh1106_set_page_cmd(page)] + sh1106_set_col_cmds(col)))


def emit_data_run(rows: List[I2CRow], addr: int, data_bytes: List[int]) -> None:
    rows.append((addr, [0x40] + [b & 0xFF for b in data_bytes]))


def emit_byte_runs_for_page(
    rows: List[I2CRow],
    addr: int,
    page: int,
    changed_cols_sorted: List[int],
    get_value_for_col,
    max_run_len: int,
) -> None:
    """
    Pack consecutive changed columns into a single 0x40 multi-byte write:
      0x00 (set page+start col)
      0x40 (bytes...)
    """
    if len(changed_cols_sorted) == 0:
        return

    run_cols: List[int] = [changed_cols_sorted[0]]

    def flush_run() -> None:
        if len(run_cols) == 0:
            return
        start_col = run_cols[0]
        emit_ctrl(rows, addr, page, start_col)
        emit_data_run(rows, addr, [get_value_for_col(c) for c in run_cols])

    for c in changed_cols_sorted[1:]:
        prev = run_cols[-1]
        consecutive = (c == prev + 1)
        too_long = (len(run_cols) >= max_run_len)
        if consecutive and not too_long:
            run_cols.append(c)
            continue
        flush_run()
        run_cols = [c]

    flush_run()


def _pixel_to_addr_page_bit_col(x: int, y: int) -> Tuple[int, int, int, int]:
    """
    Map (x,y) on stacked 132x128 canvas to (addr,page,bit,col).
    """
    if y < DISPLAY_H_SINGLE:
        addr = ADDR_TOP
        yy = y
    else:
        addr = ADDR_BOTTOM
        yy = y - DISPLAY_H_SINGLE

    page = yy // 8
    bit = yy % 8
    col = x
    return addr, page, bit, col


# -------------------------
# Image normalization
# -------------------------

def _resize_to_height(img: Image.Image, target_h: int) -> Image.Image:
    w, h = img.size
    if h == target_h:
        return img
    scale = target_h / float(h)
    new_w = int(round(w * scale))
    if new_w < 1:
        new_w = 1
    return img.resize((new_w, target_h), resample=Image.NEAREST)


def _pad_or_crop_to_width(img: Image.Image, target_w: int) -> Image.Image:
    w, h = img.size
    if w == target_w:
        return img
    if w < target_w:
        canvas = Image.new(img.mode, (target_w, h), 255 if img.mode in ("L", "RGB") else 1)
        x0 = (target_w - w) // 2
        canvas.paste(img, (x0, 0))
        return canvas
    x0 = (w - target_w) // 2
    return img.crop((x0, 0, x0 + target_w, h))


def load_any_png_to_mono_132x128(path: str, threshold: int = 128) -> np.ndarray:
    """
    Returns uint8 array shape (128,132) with values 0/1 (1 = pixel ON).
    Accepts any PNG (RGB/gray/etc).
    """
    img = Image.open(path).convert("L")
    img = _resize_to_height(img, DISPLAY_H_TOTAL)
    img = _pad_or_crop_to_width(img, DISPLAY_W)

    if img.size != (DISPLAY_W, DISPLAY_H_TOTAL):
        raise RuntimeError(f"Internal error: got {img.size}, expected {(DISPLAY_W, DISPLAY_H_TOTAL)}")

    arr = np.array(img, dtype=np.uint8)
    mono = (arr < threshold).astype(np.uint8)
    return mono


# -------------------------
# Horizontal segments (line chunks)
# -------------------------

def permute_list(items: List[T], rng: random.Random) -> List[T]:
    out = list(items)
    rng.shuffle(out)
    return out


def horizontal_lines(width: int = DISPLAY_W, height: int = DISPLAY_H_TOTAL) -> List[List[Pixel]]:
    lines: List[List[Pixel]] = []
    for y in range(height):
        line = [(x, y) for x in range(width)]
        lines.append(line)
    return lines


def chunk_lines_randomly(
    lines: List[List[Pixel]],
    rng: random.Random,
    min_len: int,
    max_len: int,
) -> List[List[Pixel]]:
    if min_len < 1:
        raise ValueError("min_len must be >= 1")
    if max_len < min_len:
        raise ValueError("max_len must be >= min_len")

    out: List[List[Pixel]] = []
    for line in lines:
        i = 0
        n = len(line)
        while i < n:
            remaining = n - i
            seg_len = rng.randint(min_len, min(max_len, remaining))
            out.append(line[i : i + seg_len])
            i += seg_len
    return out


# -------------------------
# Animation builder (multi PNG)
# -------------------------

def build_fade_over_images_rows(
    targets: List[np.ndarray],
    seed: int,
    min_seg_len: int,
    max_seg_len: int,
    max_run_len: int,
) -> List[I2CRow]:
    """
    Start at black.
    For each target image:
      transition current -> target using randomized horizontal chunks.
    Finally:
      transition current -> all-white using the same trick.
    """

    # Byte-addressable framebuffers (current display RAM state)
    fb_top = [bytearray(DISPLAY_W) for _ in range(8)]
    fb_bot = [bytearray(DISPLAY_W) for _ in range(8)]

    def get_fb(addr: int) -> List[bytearray]:
        return fb_top if addr == ADDR_TOP else fb_bot

    rows: List[I2CRow] = []

    # Build chunk "shapes" once; we will only re-permute per phase
    base_rng = random.Random(seed)
    segments = chunk_lines_randomly(
        horizontal_lines(),
        base_rng,
        min_len=min_seg_len,
        max_len=max_seg_len,
    )

    def transition_to(target: np.ndarray, phase_seed: int) -> None:
        """
        For each segment, update only the bits covered by that segment to match target (0 or 1),
        emitting packed runs per (addr,page) for bytes that change.
        """
        rng = random.Random(phase_seed)
        segs = permute_list(segments, rng)

        for seg in segs:
            if len(seg) == 0:
                continue

            # Accumulate per byte:
            #   mask_bits: which bits of that byte are affected by this segment
            #   desired_bits: among those, which should be 1
            per_byte: Dict[Tuple[int, int, int], Tuple[int, int]] = {}  # key -> (mask_bits, desired_bits)

            for (x, y) in seg:
                addr, page, bit, col = _pixel_to_addr_page_bit_col(x, y)
                key = (addr, page, col)

                mask_bits, desired_bits = per_byte.get(key, (0, 0))
                bit_mask = (1 << bit)
                mask_bits |= bit_mask
                if target[y, x] != 0:
                    desired_bits |= bit_mask
                per_byte[key] = (mask_bits, desired_bits)

            if len(per_byte) == 0:
                continue

            # Apply + record changes grouped by (addr,page)
            changed_by_page: Dict[Tuple[int, int], List[int]] = {}
            new_values: Dict[Tuple[int, int, int], int] = {}

            for (addr, page, col), (mask_bits, desired_bits) in per_byte.items():
                fb = get_fb(addr)
                old = fb[page][col]
                # overwrite only the bits in mask_bits
                new = (old & (~mask_bits & 0xFF)) | (desired_bits & 0xFF)
                if new != old:
                    fb[page][col] = new
                    new_values[(addr, page, col)] = new
                    changed_by_page.setdefault((addr, page), []).append(col)

            # Emit packed runs
            for (addr, page), cols in sorted(changed_by_page.items()):
                cols_sorted = sorted(set(cols))

                def get_value_for_col(c: int) -> int:
                    return new_values[(addr, page, c)]

                emit_byte_runs_for_page(
                    rows=rows,
                    addr=addr,
                    page=page,
                    changed_cols_sorted=cols_sorted,
                    get_value_for_col=get_value_for_col,
                    max_run_len=max_run_len,
                )

    # Transition through all images
    for i, t in enumerate(targets):
        transition_to(t, phase_seed=seed ^ (0x9E3779B9 * (i + 1)))

    # Final: transition to all-white
    # all_white = np.ones((DISPLAY_H_TOTAL, DISPLAY_W), dtype=np.uint8)
    # transition_to(all_white, phase_seed=seed ^ 0xA5A5A5A5)

    return rows


# -------------------------
# Output
# -------------------------

def write_dump(rows: List[I2CRow], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Each row: addr_hex payload_hex_bytes...\n")
        f.write("# payload starts with 00 (control) or 40 (data)\n")
        for addr, payload in rows:
            hex_bytes = " ".join(f"{b:02X}" for b in payload)
            f.write(f"0x{addr:02X} {hex_bytes}\n")


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: python gen.py out.txt img1.png img2.png ... [--seed 0xBEEF] [--min 1] [--max 12] [--run 32]")
        return 2

    outp = sys.argv[1]

    # Parse args: positional PNGs + optional flags
    pngs: List[str] = []
    seed = 0x1234
    min_seg_len = 1
    max_seg_len = 12
    max_run_len = 32

    i = 2
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--seed":
            i += 1
            seed = int(sys.argv[i], 0)
        elif a == "--min":
            i += 1
            min_seg_len = int(sys.argv[i])
        elif a == "--max":
            i += 1
            max_seg_len = int(sys.argv[i])
        elif a == "--run":
            i += 1
            max_run_len = int(sys.argv[i])
        else:
            pngs.append(a)
        i += 1

    if len(pngs) == 0:
        raise ValueError("Provide at least one PNG input.")

    targets = [load_any_png_to_mono_132x128(p) for p in pngs]
    rows = build_fade_over_images_rows(
        targets=targets,
        seed=seed,
        min_seg_len=min_seg_len,
        max_seg_len=max_seg_len,
        max_run_len=max_run_len,
    )
    write_dump(rows, outp)

    print(f"OK: wrote {len(rows)} I2C rows to {outp}")
    print(f"Inputs: {len(pngs)} images, then final all-white fade")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
