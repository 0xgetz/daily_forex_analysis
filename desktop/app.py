"""PySide6 desktop application for daily_forex_analysis.

Run with:  forex-desktop  (or  python -m desktop.app)
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QFormLayout,
    QSpinBox, QCheckBox, QMessageBox, QFileDialog, QTabWidget,
    QListWidget, QListWidgetItem,
)

from forex.config import Config
from forex.pipeline import ProviderManager, resolve_instruments, run
from forex.report import render
from desktop.chart import ChartWidget


class AnalysisWorker(QThread):
    """Run the pipeline in a background thread so the UI stays responsive."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, dry_run: bool = False):
        super().__init__()
        self.config = config
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            result = run(self.config, dry_run=self.dry_run, push=False)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class DarkPalette(QPalette):
    """GitHub-dark inspired palette."""

    def __init__(self):
        super().__init__()
        self.setColor(QPalette.Window, QColor(13, 17, 23))
        self.setColor(QPalette.WindowText, QColor(201, 209, 217))
        self.setColor(QPalette.Base, QColor(22, 27, 34))
        self.setColor(QPalette.AlternateBase, QColor(13, 17, 23))
        self.setColor(QPalette.ToolTipBase, QColor(22, 27, 34))
        self.setColor(QPalette.ToolTipText, QColor(201, 209, 217))
        self.setColor(QPalette.Text, QColor(201, 209, 217))
        self.setColor(QPalette.Button, QColor(33, 38, 45))
        self.setColor(QPalette.ButtonText, QColor(201, 209, 217))
        self.setColor(QPalette.BrightText, QColor(255, 123, 114))
        self.setColor(QPalette.Link, QColor(88, 166, 255))
        self.setColor(QPalette.Highlight, QColor(88, 166, 255))
        self.setColor(QPalette.HighlightedText, QColor(13, 17, 23))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("daily_forex_analysis — Desktop")
        self.resize(1100, 750)
        self._worker: Optional[AnalysisWorker] = None
        self._last_result: Optional[dict] = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ── Top bar ──
        top = QHBoxLayout()
        top.addWidget(QLabel("Symbols:"))
        self.symbols_edit = QLineEdit()
        self.symbols_edit.setPlaceholderText("EURUSD,GBPUSD,XAUUSD  (blank = default watchlist)")
        top.addWidget(self.symbols_edit, stretch=2)

        top.addWidget(QLabel("Timeframes:"))
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(["H1,H4,D1", "H1", "H4", "D1"])
        self.tf_combo.setEditable(True)
        top.addWidget(self.tf_combo)

        top.addWidget(QLabel("Bars:"))
        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(50, 5000)
        self.bars_spin.setValue(300)
        top.addWidget(self.bars_spin)

        self.dry_check = QCheckBox("Dry run (no LLM / file)")
        self.dry_check.setChecked(True)
        top.addWidget(self.dry_check)

        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self._on_run)
        top.addWidget(self.run_btn)

        self.export_btn = QPushButton("Export…")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        top.addWidget(self.export_btn)

        self.png_btn = QPushButton("Save PNG")
        self.png_btn.clicked.connect(self._on_save_png)
        self.png_btn.setEnabled(False)
        top.addWidget(self.png_btn)

        self.auto_check = QCheckBox("Auto-refresh (5m)")
        self.auto_check.setChecked(False)
        self.auto_check.toggled.connect(self._on_auto_toggled)
        top.addWidget(self.auto_check)

        self.refresh_timer = None
        self._refresh_interval_ms = 5 * 60 * 1000  # 5 minutes

        layout.addLayout(top)

        # ── Provider status ──
        self.provider_label = QLabel()
        self.provider_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.provider_label)
        self._refresh_providers()

        # ── Main splitter: left panel + right tabs ──
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: symbol list + quick select
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Watchlist"))
        self.symbol_list = QListWidget()
        self.symbol_list.setMaximumWidth(200)
        self.symbol_list.itemClicked.connect(self._on_symbol_selected)
        left_layout.addWidget(self.symbol_list)
        main_splitter.addWidget(left_panel)

        # Right: tabs for Table / Chart / Report
        right_tabs = QTabWidget()

        # Tab 1: Table
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "TF", "Trend", "RSI", "MACD Hist", "ATR (pips)",
            "ATR %ile", "Range Pos", "Range (pips)", "Close", "Chg (pips)",
            "Source", "Verdict",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        table_layout.addWidget(self.table)
        right_tabs.addTab(table_tab, "Table")

        # Tab 2: Chart
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        self.chart = ChartWidget()
        chart_layout.addWidget(self.chart)
        right_tabs.addTab(chart_tab, "Chart")

        # Tab 3: Report
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setFont(QFont("JetBrains Mono", 10))
        report_layout.addWidget(self.report_view)
        right_tabs.addTab(report_tab, "Report")

        main_splitter.addWidget(right_tabs)
        main_splitter.setSizes([200, 900])
        layout.addWidget(main_splitter, stretch=1)

        # ── Status bar ──
        self.statusBar().showMessage("Ready")

    # ── slots ──

    def _refresh_providers(self) -> None:
        mgr = ProviderManager()
        parts = []
        for name, state in mgr.availability_report().items():
            icon = "✓" if state == "available" else "✗"
            parts.append(f"{icon} {name}")
        self.provider_label.setText("Providers: " + "  ".join(parts))

    def _build_config(self) -> Config:
        cfg = Config.from_env()
        raw = self.symbols_edit.text().strip()
        if raw:
            cfg.symbols = [s.strip() for s in raw.split(",") if s.strip()]
        cfg.timeframes = [t.strip().upper() for t in self.tf_combo.currentText().split(",") if t.strip()]
        cfg.bars = self.bars_spin.value()
        return cfg

    def _on_run(self) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "Analysis is already running.")
            return

        cfg = self._build_config()
        dry = self.dry_check.isChecked()

        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.statusBar().showMessage("Running analysis…")

        self._worker = AnalysisWorker(cfg, dry_run=dry)
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: dict) -> None:
        self._last_result = result
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.statusBar().showMessage("Done")

        payload = result["payload"]
        summary = payload["summary"]
        self.statusBar().showMessage(
            f"Analysed {summary['succeeded']}/{summary['requested']} pairs "
            f"({summary['failed']} failed)"
        )

        self._populate_table(payload)
        self._populate_symbol_list(payload)
        self.report_view.setPlainText(result["report"])

    def _on_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.statusBar().showMessage("Error")
        QMessageBox.critical(self, "Analysis failed", msg)

    def _on_symbol_selected(self, item: QListWidgetItem) -> None:
        symbol = item.data(Qt.ItemDataRole.UserRole)
        if symbol and self._last_result:
            self._show_chart_for(symbol)

    def _show_chart_for(self, symbol: str) -> None:
        """Fetch and render the chart for one symbol."""
        if not self._last_result:
            return
        payload = self._last_result["payload"]
        pair = next((p for p in payload.get("pairs", []) if p.get("symbol") == symbol), None)
        if not pair or pair.get("error"):
            self.chart.clear()
            return

        # Re-fetch the D1 frame for charting (we don't cache frames in payload)
        from forex.providers import ProviderManager
        from forex.instruments import parse_symbol
        try:
            inst = parse_symbol(symbol)
            mgr = ProviderManager()
            candles = mgr.fetch_candles(inst, ["D1"], bars=200)
            df = candles.frames.get("D1")
            self.chart.set_data(df, pair.get("pretty", symbol))
        except Exception as exc:
            self.chart.clear()
            self.statusBar().showMessage(f"Chart unavailable: {exc}")

    def _populate_symbol_list(self, payload: dict) -> None:
        self.symbol_list.clear()
        for pair in payload.get("pairs", []):
            pretty = pair.get("pretty", "")
            symbol = pair.get("symbol", "")
            error = pair.get("error")
            item = QListWidgetItem(f"{pretty} {'✗' if error else '✓'}")
            item.setData(Qt.ItemDataRole.UserRole, symbol)
            if error:
                item.setForeground(QColor(248, 81, 73))
            self.symbol_list.addItem(item)

    def _populate_table(self, payload: dict) -> None:
        self.table.setRowCount(0)
        for pair in payload.get("pairs", []):
            if pair.get("error"):
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(pair.get("pretty", "")))
                self.table.setItem(row, 12, QTableWidgetItem(pair.get("error", "")))
                continue

            alignment = pair.get("alignment", {})
            for tf_name, read in pair.get("timeframes", {}).items():
                row = self.table.rowCount()
                self.table.insertRow(row)

                trend = read.get("trend", {})
                momentum = read.get("momentum", {})
                volatility = read.get("volatility", {})
                levels = read.get("levels", {})

                self.table.setItem(row, 0, QTableWidgetItem(pair.get("pretty", "")))
                self.table.setItem(row, 1, QTableWidgetItem(tf_name))
                self.table.setItem(row, 2, QTableWidgetItem(trend.get("direction", "")))
                self.table.setItem(row, 3, QTableWidgetItem(str(momentum.get("rsi", ""))))
                self.table.setItem(row, 4, QTableWidgetItem(str(momentum.get("macd_histogram", ""))))
                self.table.setItem(row, 5, QTableWidgetItem(str(volatility.get("atr_pips", ""))))
                self.table.setItem(row, 6, QTableWidgetItem(str(volatility.get("atr_percentile", ""))))
                pos = levels.get("position_in_range")
                self.table.setItem(row, 7, QTableWidgetItem(f"{pos*100:.0f}%" if pos is not None else ""))
                self.table.setItem(row, 8, QTableWidgetItem(str(levels.get("range_pips", ""))))
                self.table.setItem(row, 9, QTableWidgetItem(str(read.get("last_close", ""))))
                self.table.setItem(row, 10, QTableWidgetItem(str(read.get("change_pips", ""))))
                self.table.setItem(row, 11, QTableWidgetItem(pair.get("source", "")))
                self.table.setItem(row, 12, QTableWidgetItem(alignment.get("verdict", "")))

    def _on_save_png(self) -> None:
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save chart as PNG", "chart.png", "PNG (*.png)",
        )
        if not path:
            return
        self.chart.export_png(path)
        self.statusBar().showMessage(f"Chart saved to {path}")

    def _on_auto_toggled(self, checked: bool) -> None:
        from PySide6.QtCore import QTimer
        if checked:
            if self.refresh_timer is None:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self._on_run)
            self.refresh_timer.start(self._refresh_interval_ms)
            self.statusBar().showMessage("Auto-refresh every 5 minutes")
        else:
            if self.refresh_timer is not None:
                self.refresh_timer.stop()
            self.statusBar().showMessage("Auto-refresh off")

    def _on_export(self) -> None:
        if not self._last_result:
            return
        fmt, _ = QFileDialog.getSaveFileName(
            self, "Export report", "report.md",
            "Markdown (*.md);;JSON (*.json);;CSV (*.csv);;HTML (*.html)",
        )
        if not fmt:
            return
        ext = fmt.rsplit(".", 1)[-1].lower()
        payload = self._last_result["payload"]
        text = render(payload, ext)
        with open(fmt, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.statusBar().showMessage(f"Exported to {fmt}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("daily_forex_analysis")
    app.setPalette(DarkPalette())
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #0d1117; }
        QTableWidget { gridline-color: #30363d; }
        QHeaderView::section { background: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
        QPushButton { background: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 6px 14px; }
        QPushButton:hover { background: #30363d; }
        QPushButton:disabled { color: #484f58; }
        QLineEdit, QComboBox, QSpinBox { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 4px 8px; }
        QTextEdit { background: #161b22; border: 1px solid #30363d; border-radius: 6px; }
        QGroupBox { border: 1px solid #30363d; border-radius: 6px; margin-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
    """)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
