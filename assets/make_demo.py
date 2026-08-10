"""Render the demo GIF: a simulated terminal typing the command, then the real output.

The frames are drawn with Pillow rather than screen-recorded, because this box has
no terminal to record. The *content* is genuine: `demo_lines()` reads the captured
output of a real `main.py` run, so nothing on screen is invented.

Usage:
    python assets/make_demo.py /tmp/real_run.txt assets/demo.gif
"""

from __future__ import annotations

import re
import sys
from PIL import Image, ImageDraw, ImageFont

# --- terminal appearance ----------------------------------------------------

W, H = 1060, 660
PAD_X, PAD_Y = 26, 58
LINE_H = 22
FONT_SIZE = 15
# Longest line the frame can hold without touching the right edge. Measured for
# DejaVu Sans Mono at FONT_SIZE: 9px advance per glyph.
MAX_COLS = (W - PAD_X * 2) // 9

BG = (13, 17, 26)
CHROME = (24, 30, 43)
CHROME_LINE = (38, 46, 62)
FG = (200, 213, 226)
DIM = (118, 132, 150)
MINT = (46, 230, 197)
ROSE = (240, 81, 122)
YELLOW = (232, 197, 106)
BLUE = (110, 168, 246)
WHITE = (233, 246, 244)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

PROMPT = "~/daily_forex_analysis $ "
COMMAND = "python main.py --symbols EURUSD,GBPUSD,USDJPY --dry-run"

MAX_ROWS = (H - PAD_Y - 20) // LINE_H

# Markdown emphasis markers are stripped and applied as real styling, so the
# demo shows a report rather than raw source.
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
TABLE_RULE_RE = re.compile(r"^\|[\s\-:|]+\|$")

# Rules are drawn as primitives, not as repeated U+2500 glyphs: DejaVu's
# horizontal-line advance (9.03px) does not land on whole pixels, so a long run
# accumulates rounding error and shows 1-2px gaps. These sentinels tell
# render_frame to draw a line for that row instead of text.
RULE = "\x00rule"          # full-width horizontal rule
SEP = "\x00sep:"           # table header separator; suffix = column widths, csv


def load_fonts():
    return (
        ImageFont.truetype(MONO, FONT_SIZE),
        ImageFont.truetype(MONO_BOLD, FONT_SIZE),
    )


def style_line(line: str) -> list:
    """Split one report line into styled runs: [(text, bold), ...].

    Markdown emphasis is consumed rather than printed: `**x**` becomes a bold
    run and a `###`/`##`/`#` prefix bolds the whole line. Italic underscores and
    rules are handled earlier, in :func:`normalise`, because they must be gone
    before the line is wrapped.
    """
    text = line
    bold_all = False

    stripped = text.lstrip()
    lead = len(text) - len(stripped)
    for marker in ("### ", "## ", "# "):
        if stripped.startswith(marker):
            text = " " * lead + stripped[len(marker):]
            bold_all = True
            break

    if bold_all:
        return [(text, True)]

    runs, pos = [], 0
    for m in BOLD_RE.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], False))
        runs.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], False))
    return runs or [(text, False)]


def normalise(line: str) -> str:
    """Turn one raw report line into what a styled terminal would show.

    Strips italic underscores, replaces the markdown horizontal rule with a
    drawn rule, and pads table cells so the columns actually line up — raw
    unpadded pipes were the weakest thing on screen.
    """
    s = line.rstrip()

    # markdown rule -> a drawn rule (see RULE)
    if s.strip() == "---":
        return RULE

    # drop the table separator row; padded columns make it redundant
    if TABLE_RULE_RE.match(s.strip()):
        return None  # signals "skip this line"

    # italic span wrapping a whole line
    t = s.strip()
    if len(t) > 1 and t.startswith("_") and t.endswith("_"):
        lead = len(s) - len(s.lstrip())
        s = " " * lead + t[1:-1]

    return s


def align_tables(lines: list) -> list:
    """Pad every pipe-table cell to the widest value in its column.

    Emits a ``├─┼─┤`` separator under the header so it detaches from the data,
    matching how a terminal table library would render it.
    """
    out, block = [], []

    def flush():
        if not block:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block]
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        widths = [max(len(r[i]) for r in rows) for i in range(width)]

        def render(cells):
            return "  " + " │ ".join(v.ljust(widths[i]) for i, v in enumerate(cells))

        out.append(render(rows[0]))
        out.append(SEP + ",".join(str(w) for w in widths))
        for r in rows[1:]:
            out.append(render(r))
        block.clear()

    for line in lines:
        if line.lstrip().startswith("|"):
            block.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return out


def colour_for(line: str) -> tuple:
    """Syntax-colour a report line the way a terminal with ANSI would.

    Section headings are always yellow so colour means one thing at a time:
    direction is carried by the table rows and the verdict line, not by the
    heading, which otherwise made pink ambiguous between "title" and "down".
    """
    s = line.strip()
    if line == RULE or line.startswith(SEP):
        return DIM
    if s.startswith("# "):
        return WHITE
    if s.startswith("### "):
        return YELLOW
    if s.startswith("## "):
        return BLUE
    if "│" in s:  # aligned table row
        if "▲" in s:
            return MINT
        if "▼" in s:
            return ROSE
        if "→" in s:
            return DIM
        return FG
    if s.startswith("─") or s.startswith("---"):
        return DIM
    if s.startswith("Technical analysis") or s.startswith("LLM commentary"):
        return DIM
    if s.startswith("Generated:") or s.startswith("Market status:") or s.startswith("Data providers"):
        return DIM
    if "**up**" in s:
        return MINT
    if "**down**" in s:
        return ROSE
    if s.startswith("Most active during:"):
        return DIM
    return FG


def draw_chrome(img: ImageDraw.ImageDraw, font_bold) -> None:
    img.rectangle([0, 0, W, 38], fill=CHROME)
    img.line([0, 38, W, 38], fill=CHROME_LINE)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 22 + i * 22
        img.ellipse([cx - 6, 13, cx + 6, 25], fill=col)
    title = "daily_forex_analysis"
    tw = img.textlength(title, font=font_bold)
    img.text(((W - tw) / 2, 12), title, font=font_bold, fill=DIM)


def render_frame(rows, font, font_bold, cursor=False):
    """rows: list of (text, colour, force_bold) already limited to MAX_ROWS."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_chrome(d, font_bold)

    char_w = d.textlength("M", font=font)
    y = PAD_Y
    last_x = PAD_X

    for text, col, force_bold in rows:
        if text == RULE:
            ry = y + LINE_H // 2
            d.line([PAD_X, ry, PAD_X + int(char_w * 96), ry], fill=col, width=1)
            y += LINE_H
            continue

        if text.startswith(SEP):
            widths = [int(v) for v in text[len(SEP):].split(",") if v]
            ry = y + LINE_H // 2
            x = PAD_X + char_w * 2
            for i, w in enumerate(widths):
                d.line([x, ry, x + char_w * w, ry], fill=DIM, width=1)
                x += char_w * w
                if i < len(widths) - 1:
                    # the crossing sits mid-gap, under the column divider
                    d.line([x, ry, x + char_w * 3, ry], fill=DIM, width=1)
                    cx = x + char_w * 1.5
                    d.line([cx, y + 2, cx, y + LINE_H - 2], fill=DIM, width=1)
                    x += char_w * 3
            y += LINE_H
            continue

        x = PAD_X
        for run, bold in style_line(text):
            f = font_bold if (bold or force_bold) else font
            d.text((x, y), run, font=f, fill=col)
            x += d.textlength(run, font=f)
        last_x = x
        y += LINE_H

    if cursor and rows:
        d.rectangle([last_x + 1, y - LINE_H + 2, last_x + 9, y - 4], fill=MINT)

    return img


def demo_lines(path: str) -> list:
    """Load the captured real output and prepare it for the frame.

    Pipeline: normalise markdown -> align table columns -> wrap long prose at
    word boundaries with a hanging indent. Wrapping (rather than clipping) is
    what keeps text off the right edge; clipping mid-word looked broken.
    """
    import textwrap

    raw = open(path, encoding="utf-8").read().splitlines()

    normalised = []
    for line in raw:
        n = normalise(line)
        if n is not None:  # None means "drop this line" (table rule)
            normalised.append(n)

    out: list[str] = []
    for line in align_tables(normalised):
        # sentinels are drawn, not measured
        if line == RULE or line.startswith(SEP):
            out.append(line)
            continue
        # width is measured on the rendered text, after markers are stripped
        drawn = "".join(t for t, _ in style_line(line))
        if len(drawn) <= MAX_COLS:
            out.append(line)
            continue
        # aligned tables must never wrap
        if "│" in line:
            out.append(line[:MAX_COLS])
            continue
        indent = "  " if line.lstrip().startswith("- ") else ""
        wrapped = textwrap.wrap(
            line,
            width=MAX_COLS,
            subsequent_indent=indent + "  ",
            break_long_words=False,
            break_on_hyphens=False,
        )
        out.extend(wrapped or [line[:MAX_COLS]])
    return out


def build(source: str, dest: str) -> None:
    font, font_bold = load_fonts()
    frames, durations = [], []

    def add(rows, ms, cursor=False):
        frames.append(render_frame(rows[-MAX_ROWS:], font, font_bold, cursor))
        durations.append(ms)

    # 1. empty prompt
    add([(PROMPT, MINT, True)], 600, cursor=True)

    # 2. type the command. Six characters per frame keeps the frame count (and
    #    therefore the GIF's file size) reasonable while still reading as typing.
    for i in range(0, len(COMMAND) + 1, 6):
        add([(PROMPT + COMMAND[:i], FG, False)], 70, cursor=True)
    add([(PROMPT + COMMAND, FG, False)], 650, cursor=True)

    # 3. reveal the real output in small batches rather than line by line
    body = demo_lines(source)
    header = [(PROMPT + COMMAND, FG, False), ("", FG, False)]
    shown = []
    for i, line in enumerate(body):
        shown.append((line, colour_for(line), False))
        at_break = not line.strip()
        # emit a frame every other line, and always at a visual break
        if at_break or i % 2 == 1 or i == len(body) - 1:
            add(header + shown, 90 if at_break else 190)

    # 4. hold the final frame so a looping GIF is readable
    add(header + shown, 3600)

    # Quantise once against a shared palette. Per-frame palettes defeat GIF's
    # inter-frame compression and made the file larger, so the palette is built
    # from the busiest frame and reused for all of them.
    palette_source = frames[-1].convert("RGB").quantize(colors=32, dither=Image.Dither.NONE)
    paletted = [
        f.convert("RGB").quantize(palette=palette_source, dither=Image.Dither.NONE)
        for f in frames
    ]

    paletted[0].save(
        dest,
        save_all=True,
        append_images=paletted[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {dest}: {len(paletted)} frames, {sum(durations)/1000:.1f}s")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/real_run.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "assets/demo.gif"
    build(src, dst)
