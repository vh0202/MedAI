#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estimate the printed length of a build source (A4, 13pt TNR, 1.5 spacing)."""
import os
import sys

from PIL import Image

TEXT_W_CM, TEXT_H_CM = 15.5, 23.7
BODY_LINE_CM = 13 * 1.5 / 28.35          # 13pt at 1.5 spacing, pt -> cm
TABLE_LINE_CM = 10.5 * 1.05 / 28.35
WORDS_PER_LINE = 12.0                    # Vietnamese, 13pt, 15.5 cm measure
PARA_GAP_CM = 6 / 28.35


def main(src, media="media2"):
    cm = 0.0
    lines = open(src, encoding="utf-8").read().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        tag, _, rest = line.partition(" ")
        if tag == "REF":
            # 12pt, 1.15 spacing, 3pt after
            n = max(1, -(-len(rest.split()) // 13))
            cm += n * (12 * 1.15 / 28.35) + 3 / 28.35
        elif tag in ("P", "PN", "PC", "PCB", "PI", "BUL"):
            n = max(1, -(-len(rest.split()) // int(WORDS_PER_LINE)))
            cm += n * BODY_LINE_CM + PARA_GAP_CM
        elif tag in ("H1", "H1P", "H2", "H3", "H4"):
            cm += 1.6 * BODY_LINE_CM + 9 / 28.35
            if tag == "H1P":
                cm = (int(cm / TEXT_H_CM) + 1) * TEXT_H_CM   # page break
        elif tag == "PB" or tag == "SECTION":
            cm = (int(cm / TEXT_H_CM) + 1) * TEXT_H_CM
        elif tag == "FIG":
            parts = [x.strip() for x in rest.split("|")]
            w = float(parts[1])
            try:
                im = Image.open(os.path.join(media, parts[0]))
                h = w * im.size[1] / im.size[0]
            except Exception:
                h = w * 0.7
            cm += h + 0.4 + 2 * BODY_LINE_CM + PARA_GAP_CM
        elif tag == "TABLE" or tag == "TABLEX":
            cm += 2 * BODY_LINE_CM + PARA_GAP_CM              # caption
            ncol, rows = 1, 0
            while i < len(lines) and not lines[i].startswith("ENDTABLE"):
                t2, _, r2 = lines[i].strip().partition(" ")
                if t2 in ("H", "R"):
                    cells = r2.split("|")
                    ncol = max(ncol, len(cells))
                    longest = max((len(c) for c in cells), default=0)
                    per_col_chars = max(8, int(TEXT_W_CM / ncol / 0.20))
                    rows += max(1, -(-longest // per_col_chars))
                i += 1
            i += 1
            cm += rows * TABLE_LINE_CM * 1.35 + 0.6
    pages = cm / TEXT_H_CM
    print("estimated printed length: %.0f pages (A4, 13pt Times New Roman, 1.5 spacing)" % pages)
    return pages


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "media2")
