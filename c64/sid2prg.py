#!/usr/bin/env python3
import sys
from pathlib import Path

def be16(b, off):
    return (b[off] << 8) | b[off+1]

def main(in_path: str, out_path: str):
    data = Path(in_path).read_bytes()

    if len(data) < 0x10:
        raise SystemExit("File too small to be a PSID/RSID.")

    magic = data[0:4]
    if magic not in (b"PSID", b"RSID"):
        raise SystemExit("Not a PSID/RSID file (missing PSID/RSID header).")

    version    = be16(data, 0x04)
    data_offset= be16(data, 0x06)
    load_addr  = be16(data, 0x08)
    init_addr  = be16(data, 0x0A)
    play_addr  = be16(data, 0x0C)

    payload = data[data_offset:]
    if len(payload) == 0:
        raise SystemExit("No payload data found.")

    # PSID rule: if load address in header is 0, the first two bytes of payload are the load address (little-endian)
    if load_addr == 0:
        if len(payload) < 2:
            raise SystemExit("Payload too small to contain load address.")
        load_addr = payload[0] | (payload[1] << 8)
        payload = payload[2:]

    # If you *know* it must load at $4000, you can force it here:
    # load_addr = 0x4000

    prg = bytes([load_addr & 0xFF, (load_addr >> 8) & 0xFF]) + payload
    Path(out_path).write_bytes(prg)

    print(f"Magic: {magic.decode()}  version: {version}")
    print(f"Data offset: ${data_offset:04X}")
    print(f"Load: ${load_addr:04X}  Init: ${init_addr:04X}  Play: ${play_addr:04X}")
    print(f"Wrote PRG: {out_path} ({len(prg)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: sid_to_prg.py input.sid output.prg")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])
