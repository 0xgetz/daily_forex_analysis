"""Candlestick chart widget using pyqtgraph."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout

from forex.analysis import ema


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
            painter.setPen(Qt.NoPen)
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
    """Candlestick chart with optional EMA overlay."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground((13, 17, 23))
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.getAxis("bottom").setPen(pg.mkPen(color="#30363d"))
        self.plot.getAxis("left").setPen(pg.mkPen(color="#30363d"))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(color="#8b949e"))
        self.plot.getAxis("left").setTextPen(pg.mkPen(color="#8b949e"))
        layout.addWidget(self.plot)

        self._candle_item: Optional[CandlestickItem] = None
        self._ema20_line: Optional[pg.PlotDataItem] = None
        self._ema50_line: Optional[pg.PlotDataItem] = None

    def clear(self) -> None:
        self.plot.clear()
        self._candle_item = None
        self._ema20_line = None
        self._ema50_line = None

    def set_data(self, df: pd.DataFrame, instrument_name: str = "") -> None:
        """Render a candlestick chart from an OHLC DataFrame."""
        self.clear()
        if df is None or df.empty:
            return

        self._candle_item = CandlestickItem(df)
        self.plot.addItem(self._candle_item)

        # EMA overlays
        close = df["close"]
        if len(close) >= 20:
            e20 = ema(close, 20).dropna()
            x = np.arange(len(close) - len(e20), len(close))
            self._ema20_line = self.plot.plot(
                x, e20.values, pen=pg.mkPen(color="#58a6ff", width=1.5), name="EMA 20"
            )
        if len(close) >= 50:
            e50 = ema(close, 50).dropna()
            x = np.arange(len(close) - len(e50), len(close))
            self._ema50_line = self.plot.plot(
                x, e50.values, pen=pg.mkPen(color="#d29922", width=1.5), name="EMA 50"
            )

        if instrument_name:
            self.plot.setTitle(instrument_name, color="#c9d1d9", size="12pt")

        # Date axis labels (approximate: use index positions, map to timestamps)
        if isinstance(df.index, pd.DatetimeIndex):
            ticks = []
            step = max(1, len(df) // 8)
            for i in range(0, len(df), step):
                ticks.append((i, df.index[i].strftime("%m-%d %H:%M")))
            self.plot.getAxis("bottom").setTicks([ticks])

        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.enableAutoRange()
