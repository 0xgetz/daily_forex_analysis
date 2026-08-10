# Assets

Brand and demo assets, plus the scripts that regenerate them.

## Files

| File | Purpose |
| --- | --- |
| `logo.svg` | Source of truth for the logo. Hand-written SVG, no external deps. |
| `logo.png` | 512×512 raster, for places that cannot use SVG. |
| `logo-256.png` | 256×256 raster, for GitHub avatars and social cards. |
| `demo.gif` | Terminal demo shown in the README. |
| `make_demo.py` | Renders `demo.gif` from a captured report. |
| `_trim_capture.py` | Trims a captured report to the first N pairs so it fits one frame. |

## The logo

The mark is five candles rising through a faded vertical band. The band is the
London–New York overlap, the highest-liquidity window of the FX day, and its edges
land in the gaps between candles so it reads as a session rather than a stray
rectangle. The trend line is drawn *under* the candle bodies, so no body is cut.

Re-render the rasters after editing the SVG:

```bash
pip install cairosvg
python -c "import cairosvg; \
  cairosvg.svg2png(url='assets/logo.svg', write_to='assets/logo.png', output_width=512, output_height=512); \
  cairosvg.svg2png(url='assets/logo.svg', write_to='assets/logo-256.png', output_width=256, output_height=256)"
```

## The demo GIF

Every value on screen is real. The GIF is not a screen recording — this box has no
terminal to record — but the *content* is the captured stdout of an actual run, so
nothing is fabricated.

Regenerate it:

```bash
# 1. capture a real run (yfinance needs no API key)
python main.py --symbols EURUSD,GBPUSD,USDJPY --timeframes H1,H4,D1 --dry-run > /tmp/run.txt

# 2. trim to the first two pairs so the report fits one frame
python assets/_trim_capture.py /tmp/run.txt /tmp/demo.txt 2

# 3. render
pip install pillow
python assets/make_demo.py /tmp/demo.txt assets/demo.gif
```

`make_demo.py` renders the report the way a terminal with ANSI colour would: markdown
markers are consumed rather than printed, `**bold**` becomes real bold, table columns
are padded to align, and the rules are drawn as primitives.

That last detail is deliberate. Repeating `─` (U+2500) to build a rule looks correct
in a text editor but renders with 1–2 px gaps, because DejaVu Sans Mono advances
9.03 px per glyph and the fractional part accumulates. The separator and the
horizontal rule are therefore drawn with `ImageDraw.line`, which is why they measure
as a single unbroken run of lit pixels.

Colour carries one meaning at a time: yellow marks a section heading, mint an
uptrend, rose a downtrend, and dim grey a sideways read or de-emphasised text. An
earlier version coloured headings by direction too, which made pink ambiguous
between "title" and "down".
