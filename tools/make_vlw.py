#!/usr/bin/env python3
"""Convert a TrueType font to a TFT_eSPI/LovyanGFX smooth-font .vlw file.

Usage
-----
    python tools/make_vlw.py \\
        --font path/to/JetBrainsMono-Regular.ttf \\
        --size 16 \\
        --out  fonts/JBMono16.vlw

Requirements
------------
    pip install freetype-py

.vlw format (LovyanGFX / M5GFX / TFT_eSPI smooth-font)
---------------------------------------------------------
Two-section layout — ALL glyph metadata first, ALL bitmaps after:

Header (24 bytes = 6 × uint32 big-endian):
    [0] uint32  gCount      number of glyphs
    [1] uint32  version     encoder version (LovyanGFX discards this field)
    [2] uint32  yAdvance    line height in pixels
    [3] uint32  0           unused (LovyanGFX discards this field)
    [4] uint32  ascent      distance from baseline to line top (px, positive)
    [5] uint32  descent     distance from baseline to line bottom (px, positive)

Glyph metadata section (starts at byte 24, gCount × 28 bytes):
Each record = 7 × uint32 big-endian:
    [0] uint32  codepoint   Unicode code point
    [1] uint32  height      bitmap height in pixels
    [2] uint32  width       bitmap width in pixels
    [3] uint32  xAdvance    cursor advance after character (px)
    [4] int32   dY          bearing_y: distance from BASELINE to TOP of bitmap
                            (positive = above baseline; same as FreeType bitmap_top)
    [5] int32   dX          bearing_x: distance from cursor X to LEFT of bitmap
                            (positive = right of cursor; same as FreeType bitmap_left)
    [6] uint32  0           padding (unused by LovyanGFX)

Bitmap section (starts at byte 24 + gCount × 28):
    All bitmaps concatenated in glyph-record order.
    Each bitmap = width × height bytes (8bpp, one byte per pixel:
    0 = transparent, 255 = fully opaque, intermediate = anti-aliased).
    Row-major, left-to-right, top-to-bottom, NO row padding.

LovyanGFX source reference (lgfx_fonts.cpp VLWfont::loadFont / drawChar):
    bitmapPtr = 24 + gCount * 28  (start of bitmap section)
    Per-glyph seek for draw: 28 + gNum * 28  (= byte 24 + gNum*28 + 4, skips codepoint)
    dY is used as: yoffset = maxAscent - dY  (offset from line-top to glyph-top)
"""

import argparse
import struct
import sys

try:
    import freetype  # freetype-py
except ImportError:
    print("error: freetype-py not installed — run: pip install freetype-py", file=sys.stderr)
    sys.exit(1)


# Characters to include.  Encoder uses A-Z; digits and colon for the top bar.
_DEFAULT_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ":/>?[]% "
)


def _render_glyph(face: "freetype.Face", ch: str) -> dict:
    """Render one character anti-aliased (8bpp) and return its glyph record."""
    # FT_LOAD_RENDER without FT_LOAD_TARGET_MONO → greyscale 8bpp anti-aliased.
    face.load_char(ch, freetype.FT_LOAD_RENDER)
    g = face.glyph
    bm = g.bitmap

    w = bm.width
    h = bm.rows
    x_advance = g.advance.x >> 6
    dx = g.bitmap_left                  # bearing_x: cursor → left edge of bitmap
    dy = g.bitmap_top                   # bearing_y: baseline → top of bitmap (positive up)

    # Extract pixels: one byte per pixel, row-major, no pitch padding.
    bitmap = bytearray()
    for row in range(h):
        row_start = row * bm.pitch
        bitmap.extend(bm.buffer[row_start: row_start + w])

    return {
        "codepoint": ord(ch),
        "width": w,
        "height": h,
        "xAdvance": min(x_advance, 255),
        "dX": max(-128, min(127, dx)),
        "dY": max(-128, min(127, dy)),
        "bitmap": bytes(bitmap),
    }


def make_vlw(ttf_path: str, size_px: int, output_path: str, chars: str = _DEFAULT_CHARS) -> None:
    face = freetype.Face(ttf_path)
    face.set_pixel_sizes(0, size_px)

    metrics = face.size
    ascent  = metrics.ascender  >> 6        # 26.6 → integer pixels
    descent = -(metrics.descender >> 6)     # make positive
    y_advance = ascent + descent

    # Render all requested characters except space.
    glyphs = []
    skipped = []
    for ch in sorted(set(chars) - {" "}):
        try:
            glyphs.append(_render_glyph(face, ch))
        except Exception:
            skipped.append(ch)

    if skipped:
        print(f"warning: skipped {len(skipped)} chars: {''.join(skipped)}")

    # Space advance (needed for spaceWidth even though LovyanGFX recomputes it).
    face.load_char(" ", freetype.FT_LOAD_DEFAULT)
    space_width = face.glyph.advance.x >> 6

    # Sort by codepoint — LovyanGFX binary-searches the glyph list.
    glyphs.sort(key=lambda g: g["codepoint"])

    total_bitmap_bytes = sum(g["width"] * g["height"] for g in glyphs)

    with open(output_path, "wb") as f:
        # ── Header: 24 bytes (6 × uint32 big-endian) ──────────────────────────
        # LovyanGFX reads buf[0,2,4,5]; discards buf[1] (version) and buf[3].
        f.write(struct.pack(">IIIIII",
            len(glyphs),   # [0] gCount
            1,             # [1] version (discarded)
            y_advance,     # [2] yAdvance
            0,             # [3] unused
            ascent,        # [4] ascent
            descent,       # [5] descent
        ))

        # ── Glyph metadata section: gCount × 28 bytes (7 × uint32 each) ──────
        # LovyanGFX field mapping (lgfx_fonts.cpp loadFont buffer[]):
        #   [0]=codepoint [1]=height [2]=width [3]=xAdvance [4]=dY [5]=dX [6]=pad
        for g in glyphs:
            f.write(struct.pack(">IIIIiiI",
                g["codepoint"],   # [0]
                g["height"],      # [1] bitmap rows
                g["width"],       # [2] bitmap columns
                g["xAdvance"],    # [3] cursor advance
                g["dY"],          # [4] bearing_y (positive above baseline)
                g["dX"],          # [5] bearing_x (positive right of cursor)
                0,                # [6] padding
            ))

        # ── Bitmap section: all bitmaps concatenated ──────────────────────────
        # Starts at byte 24 + gCount*28 = what LovyanGFX computes as bitmapPtr.
        for g in glyphs:
            f.write(g["bitmap"])   # width × height bytes (8bpp alpha)

    sample_A = next((g for g in glyphs if g["codepoint"] == ord("A")), glyphs[0])
    advances = {g["xAdvance"] for g in glyphs if g["width"] > 0}
    expected_size = 24 + len(glyphs) * 28 + total_bitmap_bytes
    print(f"Wrote {len(glyphs)} glyphs → {output_path}")
    print(f"  File size   : {expected_size} bytes")
    print(f"  Line height : {y_advance} px  (ascent {ascent} + descent {descent})")
    print(f"  'A' bitmap  : {sample_A['width']}×{sample_A['height']} px  "
          f"bearing dX={sample_A['dX']} dY={sample_A['dY']}  "
          f"advance={sample_A['xAdvance']}")
    if len(advances) == 1:
        print(f"  Monospace   : YES (all non-empty advances = {next(iter(advances))} px)")
    else:
        print(f"  Monospace   : no  ({len(advances)} distinct advances: {sorted(advances)[:5]}…)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", required=True, metavar="TTF", help="path to .ttf or .otf file")
    ap.add_argument("--size", required=True, type=int, metavar="PX",
                    help="target glyph height in pixels")
    ap.add_argument("--out",  required=True, metavar="VLW", help="output .vlw path")
    ap.add_argument("--chars", default=_DEFAULT_CHARS, metavar="STR",
                    help="characters to include (default: A-Z a-z 0-9 punctuation)")
    args = ap.parse_args()
    make_vlw(args.font, args.size, args.out, args.chars)


if __name__ == "__main__":
    main()
