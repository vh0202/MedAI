#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalise every in-text citation to [5] / [5-7,9] / [5,9].

No spaces inside the bracket, ascending order, duplicates dropped, runs of
three or more consecutive numbers collapsed to a range.
"""
import glob
import os
import re
import sys

CITE = re.compile(r"\[([0-9][0-9,\s–—-]*)\]")


def parse(body):
    nums = []
    for part in re.split(r"[,;]", body):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)\s*[–—-]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b:
                nums.extend(range(a, b + 1))
            else:
                return None
        elif part.isdigit():
            nums.append(int(part))
        else:
            return None
    return sorted(set(nums)) or None


def render(nums):
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:                       # three or more in a row -> range
            out.append("%d-%d" % (nums[i], nums[j]))
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return "[" + ",".join(out) + "]"


def normalise_text(text, maxref=None):
    changed = [0]
    bad = []

    def sub(m):
        nums = parse(m.group(1))
        if not nums:
            bad.append(m.group(0))
            return m.group(0)
        if maxref and (nums[0] < 1 or nums[-1] > maxref):
            bad.append(m.group(0))
            return m.group(0)
        new = render(nums)
        if new != m.group(0):
            changed[0] += 1
        return new

    return CITE.sub(sub, text), changed[0], bad


def main(paths, maxref=None):
    files = []
    for p in paths:
        files.extend(sorted(glob.glob(p)) if any(c in p for c in "*?") else [p])
    total_changed, total_bad = 0, []
    for f in files:
        if not os.path.isfile(f):
            continue
        src = open(f, encoding="utf-8").read()
        out, n, bad = normalise_text(src, maxref)
        if out != src:
            open(f, "w", encoding="utf-8").write(out)
        total_changed += n
        for b in bad:
            total_bad.append((os.path.basename(f), b))
    print("citations rewritten:", total_changed)
    if total_bad:
        print("UNPARSEABLE / OUT OF RANGE:")
        for f, b in total_bad[:40]:
            print("  !", f, b)
    else:
        print("all citations parse and fall within range")
    return len(total_bad)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--max=")]
    mx = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--max=")), None)
    sys.exit(1 if main(args, mx) else 0)
