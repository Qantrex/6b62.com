#!/usr/bin/env python3
"""build.py: assemble site/index.html from src/ at exactly 27,490 bytes (0x6b62).

The page is laid out like a linker map: every block shows its own byte range and size in the
served file, and the bar on top shows all blocks as proportional segments. All of those numbers
are fixed-width fields, so filling in the real values never changes the file length.

  python3 build.py           write site/index.html
  python3 build.py --check   build in memory, compare with site/index.html, write nothing

Exits non-zero unless the output is exactly 27,490 bytes and every range checks out.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "site" / "index.html"
TOTAL = 0x6B62  # 27,490 bytes
BLOCKS = ["head", "about", "edu", "job", "work", "cert", "skills", "notes", "contact", "pad"]
MESSAGE = ("Hi, you decoded the padding. Every one of these 27,490 bytes is accounted for, "
           "and the flag is in the response headers.\n\n"
           "Since you are the kind of person who decodes padding: this page is one HTML file, built by a "
           "Python script that counts every byte, and served by nginx on a Raspberry Pi 4 at home in Vienna, "
           "through a Cloudflare Tunnel, with no open ports. No JavaScript, no trackers, no fonts to download. "
           "If you want to talk about any of it, write to konstantin@wbauer.com.\n\nKonstantin\n")
MIN_PAD_HEX = 2 * len(MESSAGE)
FIELD = re.compile(r"\{\{(\w+)\.(start|end|size|pct|hex)\}\}")


def fmt(kind, value):
    """Fixed-width fields: 0x0412 | '   910' / '27,490' | 07.3%"""
    if kind in ("start", "end"):
        return f"0x{value:04x}"
    if kind == "size":
        return f"{value:>6,}"
    if kind == "pct":
        return f"{value:04.1f}%"
    raise ValueError(kind)


def render(sources, values, pad_hex):
    """Fill every field. values: {block: {start, end, size, pct}} (all ints / floats)."""
    def sub(m):
        block, kind = m.group(1), m.group(2)
        if kind == "hex":
            return pad_hex
        return fmt(kind, values[block][kind])
    parts = [FIELD.sub(sub, sources[b]).encode("utf-8") for b in BLOCKS]
    return parts


def pad_hex(length):
    """The message in hex, then 00 bytes up to the boundary, the way a linker pads an image."""
    hex_msg = MESSAGE.encode("ascii").hex()
    if length < MIN_PAD_HEX:
        sys.exit(f"build.py: only {length} bytes left for .pad, the message needs {MIN_PAD_HEX}. "
                 f"Shorten the text by at least {MIN_PAD_HEX - length} bytes.")
    return hex_msg + "0" * (length - len(hex_msg))


def build():
    sources = {b: (SRC / f"{b}.html").read_text(encoding="utf-8") for b in BLOCKS}
    for b in BLOCKS:
        if sources[b].count("{{pad.hex}}") != (1 if b == "pad" else 0):
            sys.exit(f"build.py: {{{{pad.hex}}}} must appear exactly once, in src/pad.html ({b}.html)")

    # pass 1: dummy values (same widths) and an empty pad tell us how many bytes are left for the pad
    zero = {b: {"start": 0, "end": 0, "size": 0, "pct": 0.0} for b in BLOCKS}
    used = sum(len(p) for p in render(sources, zero, ""))
    left = TOTAL - used
    if left < 0:
        sys.exit(f"build.py: the page is {-left} bytes over 27,490 before the pad. Shorten the text.")
    hexstr = pad_hex(left - left % 2)
    if left % 2:  # an odd byte goes into the pad block as one trailing newline after the hex
        sources["pad"] = sources["pad"].replace("{{pad.hex}}", "{{pad.hex}}\n", 1)

    # pass 2: the real ranges. Field widths are fixed, so the lengths from the dummy pass still hold.
    lengths = [len(p) for p in render(sources, zero, hexstr)]
    values, pos = {}, 0
    for b, n in zip(BLOCKS, lengths):
        values[b] = {"start": pos, "end": pos + n, "size": n, "pct": round(100 * n / TOTAL, 1)}
        pos += n
    parts = render(sources, values, hexstr)
    out = b"".join(parts)

    # checks
    if len(out) != TOTAL:
        sys.exit(f"build.py: output is {len(out)} bytes, not {TOTAL}")
    for b, p, n in zip(BLOCKS, parts, lengths):
        if len(p) != n:
            sys.exit(f"build.py: block {b} changed length when its numbers were filled in")
    for b in BLOCKS:
        v = values[b]
        if out[v["start"]:v["end"]] != parts[BLOCKS.index(b)]:
            sys.exit(f"build.py: block {b} is not at {fmt('start', v['start'])}")
    if b"<script" in out.lower():
        sys.exit("build.py: the page must not contain <script")
    return out, values


def main():
    out, values = build()
    if "--check" in sys.argv[1:]:
        if not OUT.exists() or OUT.read_bytes() != out:
            sys.exit("build.py --check: site/index.html is not what src/ builds. Run ./build.py.")
    else:
        OUT.write_bytes(out)
    for b in BLOCKS:
        v = values[b]
        print(f".{b:<8} {fmt('start', v['start'])} – {fmt('end', v['end'])}  {fmt('size', v['size'])} B  {fmt('pct', v['pct'])}")
    print(f"          total  {len(out):,} B = 0x{len(out):04x}")


if __name__ == "__main__":
    main()
