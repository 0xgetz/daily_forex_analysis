"""Candlestick chart widget with RSI and MACD sub-charts using pyqtgraph."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from forex.analysis import ema, rsi, macd


class CandlestickItem(pg.GraphicsObject):
    """Draw OHLC candles as a single GraphicsObject for performance."""

    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self.data = data
        self.picture = None
        self._generate()

    def _generate(self) -> None:
        from PySide6.QtGui import QPicture, QPainter, QPen, QColor

        self.picture = QPicture()
        painter = QPainter(self.picture)

        wick_pen = QPen(QColor(139, 148, 158), 1)
        up_brush = QColor(63, 185, 80)
        down_brush = QColor(248, 81, 73)

        df = self.data
        width = 0.6

        for idx in range(len(df)):
            row = df.iloc[idx]
            o, h, l, c = row["open"], row["high"], row["low"], row["close"]

            # wick
            painter.setPen(wick_pen)
            painter.drawLine(pg.Point(idx, l), pg.Point(idx, h))

            # body
            painter.setPen(Qt.PenStyle.NoPen)
            if c >= o:
                painter.setBrush(up_brush)
                bottom, top = o, c
            else:
                painter.setBrush(down_brush)
                bottom, top = c, o
            painter.drawRect(pg.QtCore.QRectF(idx - width / 2, bottom, width, max(top - bottom, 0.00001)))

        painter.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class ChartWidget(QWidget):
    """Candlestick chart with EMA overlay, RSI and MACD sub-charts."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Main price chart ──
        self.plot = pg.PlotWidget()
        self.plot.setBackground((13, 17, 23))
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.getAxis("bottom").setPen(pg.mkPen(color="#30363d"))
        self.plot.getAxis("left").setPen(pg.mkPen(color="#30363d"))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(color="#8b949e"))
        self.plot.getAxis("left").setTextPen(pg.mkPen(color="#8b949e"))
        self.plot.hideAxis("bottom")  # hide x-axis on price chart; linked to RSI
        layout.addWidget(self.plot, stretch=3)

        # ── RSI sub-chart ──
        self.rsi_plot = pg.PlotWidget()
        self.rsi_plot.setBackground((13, 17, 23))
        self.rsi_plot.showGrid(x=True, y=True, alpha=0.10)
        self.rsi_plot.getAxis("bottom").setPen(pg.mkPen(color="#30363d"))
        self.rsi_plot.getAxis("left").setPen(pg.mkPen(color="#30363d"))
        self.rsi_plot.getAxis("bottom").setTextPen(pg.mkPen(color="#8b949e"))
        self.rsi_plot.getAxis("left").setTextPen(pg.mkPen(color="#8b949e"))
        self.rsi_plot.setMaximumHeight(120)
        self.rsi_plot.hideAxis("bottom")
        layout.addWidget(self.rsi_plot, stretch=1)

        # ── MACD sub-chart ──
        self.macd_plot = pg.PlotWidget()
        self.macd_plot.setBackground((13, 17, 23))
        self.macd_plot.showGrid(x=True, y=True, alpha=0.10)
        self.macd_plot.getAxis("bottom").setPen(pg.mkPen(color="#30363d"))
        self.macd_plot.getAxis("left").setPen(pg.mkPen(color="#30363d"))
        self.macd_plot.getAxis("bottom").setTextPen(pg.mkPen(color="#8b949e"))
        self.macd_plot.getAxis("left").setTextPen(pg.mkPen(color="#8b949e"))
        self.macd_plot.setMaximumHeight(120)
        layout.addWidget(self.macd_plot, stretch=1)

        # Link X axes so zooming one zooms all
        self.rsi_plot.setXLink(self.plot)
        self.macd_plot.setXLink(self.plot)

        self._candle_item: Optional[CandlestickItem] = None
        self._ema20_line: Optional[pg.PlotDataItem] = None
        self._ema50_line: Optional[pg.PlotDataItem] = None
        self._rsi_line: Optional[pg.PlotDataItem] = None
        self._macd_line: Optional[pg.PlotDataItem] = None
        self._signal_line: Optional[pg.PlotDataItem] = None
        self._hist_item: Optional[pg.BarGraphItem] = None

    def clear(self) -> None:
        self.plot.clear()
        self.rsi_plot.clear()
        self.macd_plot.clear()
        self._candle_item = None
        self._ema20_line = None
        self._ema50_line = None
        self._rsi_line = None
        self._macd_line = None
        self._signal_line = None
        self._hist_item = None

    def set_data(self, df: pd.DataFrame, instrument_name: str = "") -> None:
        """Render candlestick + RSI + MACD from an OHLC DataFrame."""
        self.clear()
        if df is None or df.empty:
            return

        close = df["close"]
        n = len(df)
        x = np.arange(n)

        # ── Price candles ──
        self._candle_item = CandlestickItem(df)
        self.plot.addItem(self._candle_item)

        # EMA overlays
        if n >= 20:
            e20 = ema(close, 20).dropna()
            self._ema20_line = self.plot.plot(
                x[-len(e20):], e20.values,
                pen=pg.mkPen(color="#58a6ff", width=1.5), name="EMA 20",
            )
        if n >= 50:
            e50 = ema(close, 50).dropna()
            self._ema50_line = self.plot.plot(
                x[-len(e50):], e50.values,
                pen=pg.mkPen(color="#d29922", width=1.5), name="EMA 50",
            )

        # Date axis labels
        if isinstance(df.index, pd.DatetimeIndex):
            ticks = []
            step = max(1, n // 8)
            for i in range(0, n, step):
                ticks.append((i, df.index[i].strftime("%m-%d %H:%M")))
            self.macd_plot.getAxis("bottom").setTicks([ticks])

        if instrument_name:
            self.plot.setTitle(instrument_name, color="#c9d1d9", size="12pt")

        # ── RSI ──
        if n >= 15:
            rsi_series = rsi(close, 14).dropna()
            x_rsi = np.arange(n - len(rsi_series), n)
            self._rsi_line = self.rsi_plot.plot(
                x_rsi, rsi_series.values,
                pen=pg.mkPen(color="#bc8cff", width=1.5), name="RSI 14",
            )
            # Overbought / oversold guide lines
            self.rsi_plot.addLine(y=70, pen=pg.mkPen(color="#f85149", style=Qt.PenStyle.DashLine, width=1))
            self.rsi_plot.addLine(y=30, pen=pg.mkPen(color="#3fb950", style=Qt.PenStyle.DashLine, width=1))
            self.rsi_plot.setYRange(0, 100)

        # ── MACD ──
        if n >= 35:
            macd_df = macd(close)
            macd_line = macd_df["macd"].dropna()
            signal_line = macd_df["signal"].dropna()
            hist = macd_df["histogram"].dropna()

            x_macd = np.arange(n - len(macd_line), n)
            x_sig = np.arange(n - len(signal_line), n)
            x_hist = np.arange(n - len(hist), n)

            self._macd_line = self.macd_plot.plot(
                x_macd, macd_line.values,
                pen=pg.mkPen(color="#58a6ff", width=1.5), name="MACD",
            )
            self._signal_line = self.macd_plot.plot(
                x_sig, signal_line.values,
                pen=pg.mkPen(color="#d29922", width=1.5), name="Signal",
            )

            # Histogram as bars
            colors = np.where(hist.values >= 0, "#3fb950", "#f85149")
            brushes = [pg.mkBrush(c) for c in colors]
            self._hist_item = pg.BarGraphItem(
                x=x_hist, height=hist.values, width=0.6, brushes=brushes,
            )
            self.macd_plot.addItem(self._hist_item)

        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.enableAutoRange()

    def export_png(self, path: str) -> None:
        """Save the current chart as a PNG image."""
        from pyqtgraph.exporters import ImageExporter

        # Grab the whole widget (price + RSI + MACD)
        exporter = ImageExporter(self.plot.scene())
        exporter.parameters()["width"] = 1200
        exporter.export(path)
