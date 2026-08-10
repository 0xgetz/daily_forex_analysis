"""Trim a captured report to the first N pairs so the demo fits one frame.

Keeps the real header, the first N pair sections and the real footer, so every
line shown in the GIF is genuine output — only whole pair sections are dropped.
"""

from __future__ import annotations

import sys


def trim(lines: list[str], keep_pairs: int) -> list[str]:
    out: list[str] = []
    pairs_seen = 0
    in_footer = False

    for line in lines:
        if line.startswith("### "):
            pairs_seen += 1
        if line.startswith("---") or line.startswith("_Technical analysis"):
            in_footer = True

        if in_footer or pairs_seen <= keep_pairs:
            out.append(line)

    # collapse any run of blank lines left by the removed sections
    cleaned: list[str] = []
    for line in out:
        if not line.strip() and cleaned and not cleaned[-1].strip():
            continue
        cleaned.append(line)
    return cleaned


if __name__ == "__main__":
    src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    raw = open(src, encoding="utf-8").read().splitlines()
    result = trim(raw, n)
    open(dst, "w", encoding="utf-8").write("\n".join(result) + "\n")
    print(f"{src}: {len(raw)} lines -> {dst}: {len(result)} lines ({n} pairs)")
