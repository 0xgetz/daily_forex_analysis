"""Offline tests for the desktop chart widget (offscreen Qt)."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtWidgets import QApplication  # noqa: E402

from desktop.chart import ChartWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _synthetic_ohlc(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    rng = np.random.default_rng(42)
    close = 1.15 + np.cumsum(rng.standard_normal(n) * 0.001)
    return pd.DataFrame(
        {
            "open": close - 0.0005,
            "high": close + 0.001,
            "low": close - 0.001,
            "close": close,
        },
        index=idx,
    )


class TestChartWidget:
    def test_set_data_renders_without_error(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(), "EUR/USD")
        # price plot must contain the candle item
        assert w._candle_item is not None

    def test_ema_overlays_present(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(), "EUR/USD")
        assert w._ema20_line is not None
        assert w._ema50_line is not None

    def test_rsi_subchart_drawn(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(), "EUR/USD")
        assert w._rsi_line is not None

    def test_macd_subchart_drawn(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(), "EUR/USD")
        assert w._macd_line is not None
        assert w._signal_line is not None
        assert w._hist_item is not None

    def test_short_series_skips_indicators_gracefully(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(10), "EUR/USD")
        assert w._candle_item is not None
        assert w._ema20_line is None  # < 20 bars
        assert w._rsi_line is None  # < 15 bars
        assert w._macd_line is None  # < 35 bars

    def test_empty_frame_clears(self, qapp):
        w = ChartWidget()
        w.set_data(pd.DataFrame(), "")
        assert w._candle_item is None

    def test_clear_resets_all_items(self, qapp):
        w = ChartWidget()
        w.set_data(_synthetic_ohlc(), "EUR/USD")
        w.clear()
        assert w._candle_item is None
        assert w._rsi_line is None
        assert w._macd_line is None
