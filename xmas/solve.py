#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
from PIL import Image
import numpy as np
import sys

DISPLAY_W = 132
DISPLAY_H_SINGLE = 64
DISPLAY_H_TOTAL = 128

ADDR_TOP = 0x3C
ADDR_BOTTOM = 0x3D

I2CRow = Tuple[int, List[int]]


@dataclass
class DisplayState:
    page: int
    col: int


def parse_gen_dump(path: str) -> List[I2CRow]:
    rows: List[I2CRow] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line == "" or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue

            addr_s = parts[0]
            if not addr_s.startswith("0x"):
                raise ValueError(f"Bad addr token: {addr_s!r}")
            addr = int(addr_s, 16)

            payload = [int(x, 16) for x in parts[1:]]
            rows.append((addr, payload))
    return rows


def apply_ctrl_payload(state: DisplayState, payload: List[int]) -> None:
    if len(payload) == 0 or payload[0] != 0x00:
        return

    for d in payload[1:]:
        if 0xB0 <= d <= 0xB7:
            state.page = d & 0x0F
            continue

        if d < 0x10:
            nib = d & 0x0F
            state.col = (state.col & 0xF0) | (nib << 0)
            continue

        if d < 0x20:
            nib = d & 0x0F
            state.col = (nib << 4) | (state.col & 0x0F)
            continue


def write_data_to_fb(fb: np.ndarray, state: DisplayState, payload: List[int]) -> None:
    """
    fb: uint8 array shape (64,132) with values 0/1
    payload: [0x40, ...bytes]
    """
    if len(payload) == 0 or payload[0] != 0x40:
        return

    page = state.page
    col = state.col
    y_base = page * 8

    data = payload[1:]
    for b in data:
        if 0 <= page <= 7 and 0 <= col < DISPLAY_W:
            # Set 8 vertical pixels from bits
            for bit in range(8):
                y = y_base + bit
                if 0 <= y < DISPLAY_H_SINGLE:
                    fb[y, col] = 1 if ((b >> bit) & 1) != 0 else 0
        col += 1

    state.col = col


def fb_to_image(top_fb: np.ndarray, bottom_fb: np.ndarray) -> Image.Image:
    """
    Convert two (64,132) uint8 0/1 buffers to a single 132x128 'L' image.
    """
    full = np.zeros((DISPLAY_H_TOTAL, DISPLAY_W), dtype=np.uint8)
    full[0:DISPLAY_H_SINGLE, :] = top_fb * 255
    full[DISPLAY_H_SINGLE:DISPLAY_H_TOTAL, :] = bottom_fb * 255
    return Image.fromarray(full, mode="L")


def scale_frame(img: Image.Image, scale: int) -> Image.Image:
    if scale <= 1:
        return img
    return img.resize((img.size[0] * scale, img.size[1] * scale), resample=Image.NEAREST)


def make_black_frame(scale: int) -> Image.Image:
    img = Image.new("L", (DISPLAY_W, DISPLAY_H_TOTAL), 0)
    return scale_frame(img, scale)


def solve(
    gen_dump_path: str,
    out_gif_path: str,
    scale: int,
    delay_ms: int,
    frame_stride: int,
) -> None:
    rows = parse_gen_dump(gen_dump_path)

    top_fb = np.zeros((DISPLAY_H_SINGLE, DISPLAY_W), dtype=np.uint8)
    bottom_fb = np.zeros((DISPLAY_H_SINGLE, DISPLAY_W), dtype=np.uint8)

    states: Dict[int, DisplayState] = {
        ADDR_TOP: DisplayState(page=0, col=0),
        ADDR_BOTTOM: DisplayState(page=0, col=0),
    }

    frames: List[Image.Image] = [make_black_frame(scale)]

    data_count = 0
    for addr, payload in rows:
        state = states.get(addr)
        if state is None or len(payload) == 0:
            continue

        first = payload[0]
        if first == 0x00:
            apply_ctrl_payload(state, payload)
            continue

        if first == 0x40:
            if addr == ADDR_TOP:
                write_data_to_fb(top_fb, state, payload)
            elif addr == ADDR_BOTTOM:
                write_data_to_fb(bottom_fb, state, payload)

            data_count += 1

            # "emit a frame after each 0x40" logically,
            # but only *record* every Nth to speed up playback.
            if frame_stride == 1 or (data_count % frame_stride) == 0:
                frame = fb_to_image(top_fb, bottom_fb)
                frames.append(scale_frame(frame, scale))

    if len(frames) == 0:
        raise RuntimeError("No frames produced.")

    # Palette conversion once per frame
    pal_frames: List[Image.Image] = [
        fr.convert("P", palette=Image.Palette.ADAPTIVE, colors=2) for fr in frames
    ]

    # Many viewers clamp GIF delays; combine with frame_stride.
    pal_frames[0].save(
        out_gif_path,
        save_all=True,
        append_images=pal_frames[1:],
        duration=delay_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python solve.py gen_out.txt out.gif [scale] [delay_ms] [frame_stride]")
        print("  scale: default 4")
        print("  delay_ms: default 10 (GIF viewers often clamp below 10ms anyway)")
        print("  frame_stride: save every Nth 0x40 (default 8). 1 = save all.")
        return 2

    gen_dump_path = sys.argv[1]
    out_gif_path = sys.argv[2]

    scale = 4
    delay_ms = 10
    frame_stride = 8

    if len(sys.argv) >= 4:
        scale = int(sys.argv[3])
    if len(sys.argv) >= 5:
        delay_ms = int(sys.argv[4])
    if len(sys.argv) >= 6:
        frame_stride = int(sys.argv[5])

    if scale < 1:
        raise ValueError("scale must be >= 1")
    if delay_ms < 0:
        raise ValueError("delay_ms must be >= 0")
    if frame_stride < 1:
        raise ValueError("frame_stride must be >= 1")

    solve(gen_dump_path, out_gif_path, scale, delay_ms, frame_stride)
    print(f"OK: wrote {out_gif_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
