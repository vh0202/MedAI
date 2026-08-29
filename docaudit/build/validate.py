#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural QA for the generated monograph."""
import re
import sys
import zipfile
from collections import Counter

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def main(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    print("== parts ==")
    print(" footers:", [n for n in names if "footer" in n])
    print(" media:", len([n for n in names if n.startswith("word/media/")]))

    doc = etree.fromstring(z.read("word/document.xml"))
    styles = etree.fromstring(z.read("word/styles.xml"))

    # ---- fonts -----------------------------------------------------------
    bad_fonts = Counter()
    for rf in doc.iter(W + "rFonts"):
        for a in ("ascii", "hAnsi", "eastAsia", "cs"):
            v = rf.get(W + a)
            if v and v != "Times New Roman":
                bad_fonts[v] += 1
    for rf in styles.iter(W + "rFonts"):
        for a in ("ascii", "hAnsi", "eastAsia", "cs"):
            v = rf.get(W + a)
            if v and v != "Times New Roman":
                bad_fonts["style:" + v] += 1
    runs_total = len(list(doc.iter(W + "r")))
    runs_with_font = 0
    for r in doc.iter(W + "r"):
        rpr = r.find(W + "rPr")
        if rpr is not None and rpr.find(W + "rFonts") is not None:
            runs_with_font += 1
    print("== fonts ==")
    print(" non-TNR font refs:", dict(bad_fonts) or "none")
    print(" runs:", runs_total, "with explicit rFonts:", runs_with_font)

    # ---- theme fonts (Word falls back to these if a run lacks rFonts) -----
    if "word/theme/theme1.xml" in names:
        th = z.read("word/theme/theme1.xml").decode("utf-8")
        latin = re.findall(r'<a:latin typeface="([^"]*)"', th)
        print(" theme latin typefaces:", sorted(set(latin)))

    # ---- headings --------------------------------------------------------
    def text_of(p):
        return "".join(t.text or "" for t in p.iter(W + "t"))

    levels = Counter()
    headings = []
    for p in doc.iter(W + "p"):
        ppr = p.find(W + "pPr")
        if ppr is None:
            continue
        ps = ppr.find(W + "pStyle")
        if ps is None:
            continue
        v = ps.get(W + "val")
        if v and v.startswith("Heading"):
            lvl = int(v.replace("Heading", ""))
            levels[lvl] += 1
            headings.append((lvl, text_of(p)))
    print("== headings ==", dict(sorted(levels.items())))

    # numbering sanity
    problems = []
    for lvl, t in headings:
        t = t.strip()
        if lvl == 2 and not re.match(r"^\d+\.\d+\.", t):
            problems.append("H2 not numbered x.y: " + t[:60])
        if lvl == 3 and not re.match(r"^\d+\.\d+\.\d+\.", t):
            problems.append("H3 not numbered x.y.z: " + t[:60])
        if lvl == 4 and not re.match(r"^\d+\.\d+\.\d+\.\d+\.", t):
            problems.append("H4 not numbered x.y.z.w: " + t[:60])
    for p in problems[:20]:
        print("  !", p)
    print("  heading numbering problems:", len(problems))

    # ---- tables ----------------------------------------------------------
    tbls = list(doc.iter(W + "tbl"))
    print("== tables ==", len(tbls))
    for i, tb in enumerate(tbls, 1):
        grid = tb.find(W + "tblGrid")
        ws = [int(gc.get(W + "w")) for gc in grid.findall(W + "gridCol")]
        total_cm = sum(ws) / 567.0
        rows = tb.findall(W + "tr")
        ncols = [len(r.findall(W + "tc")) for r in rows]
        hdr = rows[0].find(W + "trPr") is not None and rows[0].find(W + "trPr").find(W + "tblHeader") is not None
        ok = abs(total_cm - 15.5) < 0.15 and len(set(ncols)) == 1 and hdr
        if not ok:
            print("  ! table %d width=%.2fcm cols=%s headerRepeat=%s" % (i, total_cm, set(ncols), hdr))
    widths_ok = all(
        abs(sum(int(gc.get(W + "w")) for gc in tb.find(W + "tblGrid").findall(W + "gridCol")) / 567.0 - 15.5) < 0.15
        for tb in tbls
    )
    print("  all tables span the 15.5 cm text width:", widths_ok)

    # ---- captions --------------------------------------------------------
    caps = []
    for p in doc.iter(W + "p"):
        t = text_of(p).strip()
        has_pageref = any(
            (i.text or "").strip().startswith("PAGEREF") for i in p.iter(W + "instrText")
        )
        if has_pageref:
            continue
        if re.match(r"^(Bảng|Hình)\s+\d+\.\d+\.", t):
            caps.append(t)
    tabcaps = [c for c in caps if c.startswith("Bảng")]
    figcaps = [c for c in caps if c.startswith("Hình")]
    print("== captions ==", "tables:", len(tabcaps), "figures:", len(figcaps))
    bad_caps = [c for c in caps if not re.search(r"\[[0-9,\-\s]+\]\s*\.?\s*$", c)]
    for c in bad_caps:
        print("  ! caption without trailing citation:", c[:90])
    src = [c for c in caps if "Nguồn" in c or "nguồn:" in c]
    print("  captions containing 'Nguồn':", len(src))
    # duplicate / sequence check
    for kind, lst in (("Bảng", tabcaps), ("Hình", figcaps)):
        nums = [re.match(r"^%s\s+(\d+)\.(\d+)\." % kind, c).groups() for c in lst]
        seq = {}
        for a, b in nums:
            seq.setdefault(int(a), []).append(int(b))
        for ch, v in sorted(seq.items()):
            if v != list(range(1, len(v) + 1)):
                print("  ! %s numbering gap in chapter %d: %s" % (kind, ch, v))
        print("  %s per chapter: %s" % (kind, {k: len(v) for k, v in sorted(seq.items())}))

    # ---- images ----------------------------------------------------------
    print("== images ==", len(list(doc.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"))))

    # ---- word count ------------------------------------------------------
    all_text = []
    for p in doc.iter(W + "p"):
        all_text.append(text_of(p))
    body = "\n".join(all_text)
    print("== word count ==")
    print("  total words (incl. tables, refs, front matter):", len(body.split()))

    # words excluding the reference list
    idx = body.rfind("TÀI LIỆU THAM KHẢO")
    if idx > 0:
        print("  words before TÀI LIỆU THAM KHẢO:", len(body[:idx].split()))
        print("  reference-list words:", len(body[idx:].split()))

    # ---- citations -------------------------------------------------------
    refs = re.findall(r"^\s*(\d+)\.\s+[A-ZĐÀ-Ỹ]", body[idx:] if idx > 0 else "", re.M)
    maxref = max((int(r) for r in refs), default=0)
    cited = set()
    for m in re.finditer(r"\[([0-9,\-\s]+)\]", body[:idx] if idx > 0 else body):
        for part in m.group(1).split(","):
            part = part.strip()
            if "-" in part:
                try:
                    a, b = part.split("-")
                    cited.update(range(int(a), int(b) + 1))
                except ValueError:
                    pass
            elif part.isdigit():
                cited.add(int(part))
    print("== citations ==")
    print("  reference entries detected:", maxref)
    print("  distinct refs cited in text:", len(cited))
    if maxref:
        missing = sorted(set(range(1, maxref + 1)) - cited)
        over = sorted(c for c in cited if c > maxref)
        print("  NEVER cited:", missing or "none")
        print("  cited but out of range:", over or "none")

    # ---- fields ----------------------------------------------------------
    instrs = [i.text for i in doc.iter(W + "instrText") if i.text]
    print("== fields ==", Counter(t.strip().split()[0] for t in instrs if t.strip()))


if __name__ == "__main__":
    main(sys.argv[1])
