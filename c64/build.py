from pathlib import Path
import subprocess

prog_bas   = Path("prog.bas")     # tokenized BASIC (load addr $0801)
prog_prg   = Path("prog.prg")     # tokenized BASIC (load addr $0801)
screen_bin = Path("screen.bin")   # 1000 bytes
color_bin  = Path("color.bin")    # 1000 bytes
out_prg    = Path("xmas.prg")

REM_START_LINE = 9000
REM_STEP = 10
REM_CHUNK = 10000  # bytes per REM line (adjust if you want)

# If you insist on "no escaping", these MUST NOT appear in REM data:
# 0   terminates the BASIC line
FORBIDDEN = {0}

def run_petcat(bas_path: Path, prg_path: Path) -> None:
    subprocess.run(
        ["petcat", "-w2", "-o", str(prg_path), str(bas_path)],
        check=True,
    )

def read_u16_le(b: bytes, off: int) -> int:
    return b[off] | (b[off + 1] << 8)

def write_u16_le(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF])

run_petcat(prog_bas, prog_prg)

# Load existing PRG
prg = prog_prg.read_bytes()
if len(prg) < 2:
    raise SystemExit("prog.prg is too short")

load_addr = read_u16_le(prg, 0)
if load_addr != 0x0801:
    raise SystemExit(f"expected load address $0801, got ${load_addr:04x}")

prog = bytearray(prg[2:])  # tokenized BASIC bytes

# Find end-of-program (line with next ptr = 0)
# Each line: nextptr(2), lineno(2), ... , 0
off = 0
while True:
    if off + 2 > len(prog):
        raise SystemExit("corrupt BASIC program (ran off end while scanning next ptr)")
    next_ptr = read_u16_le(prog, off)

    if next_ptr == 0:
        # This is the 2-byte end marker, not a normal line header.
        end_off = off
        break

    # Normal line: must have at least nextptr+lineno
    if off + 4 > len(prog):
        raise SystemExit("corrupt BASIC program (truncated line header)")

    # next_ptr is an absolute address in memory
    off = next_ptr - load_addr
    if off < 0 or off >= len(prog):
        raise SystemExit("corrupt BASIC program (next pointer out of range)")
    
# Build interleaved data
screen = screen_bin.read_bytes()
color  = color_bin.read_bytes()

if len(screen) != 1000:
    raise SystemExit(f"screen.bin must be 1000 bytes, got {len(screen)}")
if len(color) != 1000:
    raise SystemExit(f"color.bin must be 1000 bytes, got {len(color)}")

interleaved = bytearray()
for i in range(1000):
    interleaved.append(screen[i])
    interleaved.append(color[i])

# Strict assertion: no forbidden bytes
bad = sorted(set(interleaved).intersection(FORBIDDEN))
if len(bad) != 0:
    # This is the REAL reason REM blobs "don't go through": 0 truncates the line.
    raise SystemExit(
        f"interleaved data contains forbidden byte(s): {bad}. "
        "you cannot store 0 inside a tokenized BASIC REM line without escaping."
    )

# Remove the terminating end line (we'll replace it with our new lines)
prog = prog[:end_off]

# Append REM lines
line_no = REM_START_LINE
cursor_off = len(prog)

for i in range(0, len(interleaved), REM_CHUNK):
    chunk = bytes(interleaved[i:i+REM_CHUNK])

    line_start_addr = load_addr + cursor_off
    # line layout: nextptr(2) lineno(2) REMtoken(1) data(N) 0(1)
    line_len = 2 + 2 + 1 + len(chunk) + 1
    next_line_addr = line_start_addr + line_len

    # next ptr (filled now; overwritten later for last line)
    prog += write_u16_le(next_line_addr)
    # line number
    prog += write_u16_le(line_no)
    # REM token is $8F in BASIC V2
    prog += bytes([0x8F])
    # raw blob (no extra space; your BASIC reader uses addr+5)
    prog += chunk
    # end of line
    prog += bytes([0x00])

    cursor_off += line_len
    line_no += REM_STEP

# Terminate program: final line's next ptr must be 0
# Overwrite the last appended line's next pointer with 0.
# That pointer is at the start of the last line:
# last_line_start_off = (end of prog) - last_line_len
# Easiest: scan backwards to find last line start:
# We'll compute it from cursor_off and last line length used.
last_chunk_len = len(interleaved) % REM_CHUNK
if last_chunk_len == 0:
    last_chunk_len = REM_CHUNK
last_line_len = 2 + 2 + 1 + last_chunk_len + 1
last_line_start_off = len(prog) - last_line_len
prog[last_line_start_off:last_line_start_off+2] = b"\x00\x00"

# Write final PRG
out_prg.write_bytes(write_u16_le(load_addr) + bytes(prog))
print(f"wrote {out_prg} ({len(out_prg.read_bytes())} bytes)")
