"""Tests for the demo-GIF text pipeline in assets/make_demo.py.

The image rendering itself is not asserted here — comparing rasters is brittle
and the drawing code is a one-shot generator. What *is* worth pinning are the
pure text transforms, because they are where the visual defects actually came
from: markdown leaking through as literal `**`, unaligned table columns, and
lines running past the right edge.

``assets`` is not a package, so the module is loaded by path.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_MODULE_PATH = os.path.join(_ASSETS, "make_demo.py")

pytest.importorskip("PIL", reason="Pillow is only needed for demo-asset generation")


def _load():
    spec = importlib.util.spec_from_file_location("make_demo", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_demo"] = module
    spec.loader.exec_module(module)
    return module


md = _load()


class TestStyleLine:
    """Markdown emphasis must be consumed, never printed."""

    def _drawn(self, line):
        return "".join(text for text, _ in md.style_line(line))

    def test_bold_span_becomes_a_bold_run(self):
        runs = md.style_line("Multi-timeframe read: **up** (confidence: medium)")
        assert ("up", True) in runs
        assert "**" not in self._drawn("Multi-timeframe read: **up** (confidence: medium)")

    def test_multiple_bold_spans(self):
        runs = md.style_line("**a** and **b**")
        assert [t for t, b in runs if b] == ["a", "b"]

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("# Daily Forex Analysis", "Daily Forex Analysis"),
            ("## Pairs", "Pairs"),
            ("### EUR/USD  ▲", "EUR/USD  ▲"),
        ],
    )
    def test_heading_marker_stripped_and_bolded(self, line, expected):
        runs = md.style_line(line)
        assert runs == [(expected, True)]

    def test_plain_line_is_one_unbolded_run(self):
        assert md.style_line("Last price 1.15540") == [("Last price 1.15540", False)]

    def test_empty_line_survives(self):
        assert self._drawn("") == ""

    def test_arrow_glyphs_preserved(self):
        """The direction glyphs carry meaning and must not be mangled."""
        for glyph in ("▲", "▼", "→"):
            assert glyph in self._drawn(f"| H1 | {glyph} up |")


class TestNormalise:
    def test_horizontal_rule_becomes_sentinel(self):
        assert md.normalise("---") == md.RULE

    def test_table_separator_row_is_dropped(self):
        assert md.normalise("| --- | --- | --- |") is None

    def test_italic_wrapper_stripped(self):
        out = md.normalise("_Technical analysis for educational purposes._")
        assert out == "Technical analysis for educational purposes."

    def test_italic_wrapper_preserves_indent(self):
        assert md.normalise("  _note._") == "  note."

    def test_ordinary_line_untouched(self):
        assert md.normalise("Last price 1.15540") == "Last price 1.15540"

    def test_lone_underscore_not_treated_as_italic(self):
        assert md.normalise("_") == "_"

    def test_trailing_whitespace_removed(self):
        assert md.normalise("value   ") == "value"


class TestAlignTables:
    HEADER = "| Timeframe | Trend | RSI |"
    ROWS = [
        "| H1 | ▲ up | 53.0 |",
        "| D1 | → sideways | 60.4 |",
    ]

    def _aligned(self):
        return md.align_tables([self.HEADER] + self.ROWS)

    def test_emits_header_separator_then_rows(self):
        out = self._aligned()
        assert len(out) == 4
        assert out[1].startswith(md.SEP)

    def test_columns_line_up_across_every_row(self):
        """The defect this guards: per-row padding left dividers ragged."""
        out = self._aligned()
        text_rows = [out[0]] + out[2:]
        positions = [
            [i for i, ch in enumerate(row) if ch == "│"] for row in text_rows
        ]
        assert positions[0] == positions[1] == positions[2]

    def test_separator_widths_match_rendered_columns(self):
        out = self._aligned()
        widths = [int(v) for v in out[1][len(md.SEP):].split(",")]
        # widest cell per column: Timeframe(9), "→ sideways"(10), RSI(4)
        assert widths == [9, 10, 4]

    def test_cell_values_survive_padding(self):
        out = self._aligned()
        assert "▲ up" in out[2]
        assert "→ sideways" in out[3]
        assert "60.4" in out[3]

    def test_non_table_lines_pass_through_in_order(self):
        out = md.align_tables(["before", self.HEADER, self.ROWS[0], "after"])
        assert out[0] == "before"
        assert out[-1] == "after"

    def test_two_separate_tables_are_padded_independently(self):
        lines = [
            "| a | b |",
            "| 1 | 2 |",
            "",
            "| longer-header | x |",
            "| 3 | 4 |",
        ]
        out = md.align_tables(lines)
        assert out.count("") == 1
        assert sum(1 for line in out if line.startswith(md.SEP)) == 2

    def test_ragged_row_is_padded_not_dropped(self):
        out = md.align_tables(["| a | b | c |", "| 1 |"])
        assert len(out) == 3  # header, separator, row


class TestDemoLines:
    """End-to-end: a captured report becomes frame-ready lines."""

    SAMPLE = """# Daily Forex Analysis

## Pairs

### EUR/USD  ▲

Multi-timeframe read: **up** (confidence: medium)

| Timeframe | Trend | RSI |
| --- | --- | --- |
| H1 | ▲ up | 53.0 |
| D1 | → sideways | 60.4 |

- **H1**: fast EMA above slow EMA by 7.4 pips. RSI 53.0 mid-range; MACD histogram negative. ATR 7.0 pips (percentile 11 of recent history); compressed ranges often precede breakouts. High 1.158212, low 1.152206.

---

_Technical analysis generated from public market data for educational purposes. Not investment advice._
"""

    @pytest.fixture
    def lines(self, tmp_path):
        path = tmp_path / "report.txt"
        path.write_text(self.SAMPLE, encoding="utf-8")
        return md.demo_lines(str(path))

    def test_no_line_exceeds_the_frame_width(self, lines):
        """The original defect: long prose was clipped mid-word at the edge."""
        for line in lines:
            if line == md.RULE or line.startswith(md.SEP):
                continue
            drawn = "".join(t for t, _ in md.style_line(line))
            assert len(drawn) <= md.MAX_COLS, f"too wide ({len(drawn)}): {drawn!r}"

    def test_no_literal_markdown_survives(self, lines):
        for line in lines:
            if line == md.RULE or line.startswith(md.SEP):
                continue
            drawn = "".join(t for t, _ in md.style_line(line))
            assert "**" not in drawn
            assert not drawn.lstrip().startswith("#")
            assert not drawn.strip().startswith("_")
            assert "|" not in drawn  # pipes replaced by box-drawing dividers

    def test_long_prose_is_wrapped_not_truncated(self, lines):
        """Wrapped text must still end with the source's final words."""
        joined = " ".join(lines)
        assert "low 1.152206." in joined

    def test_rule_and_separator_sentinels_present(self, lines):
        assert md.RULE in lines
        assert any(line.startswith(md.SEP) for line in lines)

    def test_table_rows_use_box_drawing_dividers(self, lines):
        table = [line for line in lines if "│" in line]
        assert len(table) == 3  # header + 2 data rows

    def test_headings_retain_their_text(self, lines):
        drawn = ["".join(t for t, _ in md.style_line(line)) for line in lines]
        assert "Daily Forex Analysis" in drawn
        assert any("EUR/USD" in d for d in drawn)


class TestColourFor:
    def test_uptrend_row_is_mint(self):
        assert md.colour_for("  H1 │ ▲ up │ 53.0") == md.MINT

    def test_downtrend_row_is_rose(self):
        assert md.colour_for("  H1 │ ▼ down │ 21.0") == md.ROSE

    def test_sideways_row_is_dim(self):
        assert md.colour_for("  D1 │ → sideways │ 60.4") == md.DIM

    def test_heading_colour_is_independent_of_direction(self):
        """Regression: headings were once coloured by direction, so pink meant
        both "section title" and "downtrend"."""
        assert md.colour_for("### EUR/USD  ▲") == md.YELLOW
        assert md.colour_for("### USD/JPY  ▼") == md.YELLOW

    def test_verdict_lines_carry_direction(self):
        assert md.colour_for("Multi-timeframe read: **up** (confidence: high)") == md.MINT
        assert md.colour_for("Multi-timeframe read: **down** (confidence: high)") == md.ROSE

    def test_sentinels_are_dim(self):
        assert md.colour_for(md.RULE) == md.DIM
        assert md.colour_for(md.SEP + "9,10,4") == md.DIM

    def test_metadata_is_dim(self):
        for line in ("Generated: 2026-08-10", "Market status: Tokyo", "Data providers available: yfinance"):
            assert md.colour_for(line) == md.DIM

    def test_body_text_is_default(self):
        assert md.colour_for("Last price 1.15540 (source: yfinance)") == md.FG
