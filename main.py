#!/usr/bin/env python3
"""Command-line entry point for daily_forex_analysis.

Examples:
    python main.py                            # default watchlist, keyless provider
    python main.py --symbols EURUSD,USDJPY    # pick your pairs
    python main.py --dry-run                  # no LLM call, no file write
    python main.py --check                    # show configuration and exit
    python main.py --format json              # machine-readable output
"""

from __future__ import annotations

import argparse
import logging
import sys

from forex.config import Config
from forex.instruments import InvalidSymbolError
from forex.pipeline import ProviderManager, resolve_instruments, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="daily_forex_analysis",
        description="LLM-assisted technical analysis for spot FX and metals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--symbols",
        help="Comma-separated pairs, e.g. EURUSD,GBPUSD,XAUUSD. Overrides FOREX_SYMBOLS.",
    )
    parser.add_argument(
        "--timeframes",
        help="Comma-separated timeframes from H1,H4,D1 (default: all three).",
    )
    parser.add_argument("--bars", type=int, help="Candles to request per timeframe (default 300).")
    parser.add_argument("--provider", help="Preferred provider: twelvedata, alphavantage, yfinance.")
    parser.add_argument("--format", dest="fmt", choices=("markdown", "json"), help="Report format.")
    parser.add_argument("--output-dir", help="Directory for report files (default: reports).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyse and print only: no LLM call, no file written, no notification.",
    )
    parser.add_argument("--no-push", action="store_true", help="Skip notifications.")
    parser.add_argument("--stdout", action="store_true", help="Print the report to stdout.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print configuration and provider availability, then exit.",
    )
    parser.add_argument("--log-level", help="DEBUG, INFO, WARNING, ERROR.")
    return parser


def apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    if args.symbols:
        config.symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if args.timeframes:
        config.timeframes = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]
    if args.bars:
        config.bars = args.bars
    if args.provider:
        config.preferred_provider = args.provider
    if args.fmt:
        config.report_format = args.fmt
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.log_level:
        config.log_level = args.log_level.upper()
    return config


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = apply_overrides(Config.from_env(), args)

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if args.check:
        print("Configuration")
        print("-------------")
        print(config.describe())
        print()
        print("Data providers")
        print("--------------")
        for name, state in ProviderManager(preferred=config.preferred_provider or None).availability_report().items():
            print(f"  {name}: {state}")
        print()
        try:
            print("Resolved symbols: " + ", ".join(i.pretty for i in resolve_instruments(config)))
        except InvalidSymbolError as exc:
            print(f"Symbol error: {exc}", file=sys.stderr)
            return 2
        return 0

    try:
        resolve_instruments(config)
    except InvalidSymbolError as exc:
        print(f"Symbol error: {exc}", file=sys.stderr)
        return 2

    result = run(config, dry_run=args.dry_run, push=not args.no_push)
    payload = result["payload"]
    summary = payload["summary"]

    if args.stdout or args.dry_run:
        print(result["report"])

    if result["path"]:
        print(f"Report written to {result['path']}", file=sys.stderr)

    for channel, ok in (result["notifications"] or {}).items():
        print(f"Notification {channel}: {'sent' if ok else 'failed'}", file=sys.stderr)

    print(
        f"Analysed {summary['succeeded']}/{summary['requested']} pairs "
        f"({summary['failed']} failed)",
        file=sys.stderr,
    )

    # Non-zero only when nothing at all could be analysed.
    return 0 if summary["succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
