"""Pipeline orchestration: fetch -> analyse -> interpret -> render -> notify.

One instrument failing must never abort the run, so each pair is wrapped
individually and its error recorded in the payload.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import report as report_module
from .analysis import align_timeframes, analyse_timeframe
from .config import Config
from .instruments import Instrument, default_watchlist, parse_symbols
from .llm import generate_commentary
from .notify import notify
from .providers import AllProvidersFailedError, ProviderManager
from .sessions import relevant_sessions_for, session_summary

logger = logging.getLogger(__name__)


def resolve_instruments(config: Config) -> List[Instrument]:
    """Symbols from config, falling back to the default watchlist."""
    if config.symbols:
        return parse_symbols(config.symbols)
    return default_watchlist()


def analyse_instrument(
    instrument: Instrument,
    manager: ProviderManager,
    timeframes: List[str],
    bars: int,
) -> Dict[str, Any]:
    """Fetch and analyse one instrument, capturing failure in the result."""
    entry: Dict[str, Any] = {
        "symbol": instrument.symbol,
        "pretty": instrument.pretty,
        "pip_size": instrument.pip_size,
        "relevant_sessions": [s.name for s in relevant_sessions_for(instrument.base, instrument.quote)],
    }

    try:
        candles = manager.fetch_candles(instrument, timeframes, bars)
    except AllProvidersFailedError as exc:
        entry["error"] = str(exc)
        return entry
    except Exception as exc:  # defensive: a provider bug must not kill the run
        logger.exception("unexpected error fetching %s", instrument.symbol)
        entry["error"] = f"unexpected fetch error: {exc}"
        return entry

    reads = {}
    for timeframe in candles.timeframes():
        frame = candles.frames[timeframe]
        try:
            reads[timeframe] = analyse_timeframe(frame, instrument, timeframe)
        except Exception as exc:
            logger.warning("analysis failed for %s %s: %s", instrument.symbol, timeframe, exc)

    if not reads:
        entry["error"] = "no timeframe could be analysed"
        return entry

    last_price = next(
        (r.last_close for r in reads.values() if r.last_close is not None), None
    )

    entry["source"] = candles.source
    entry["last_price"] = last_price
    entry["last_price_display"] = (
        instrument.format_price(last_price) if last_price is not None else "n/a"
    )
    entry["timeframes"] = {tf: read.to_dict() for tf, read in reads.items()}
    entry["alignment"] = align_timeframes(reads)
    return entry


def build_payload(config: Config, manager: Optional[ProviderManager] = None) -> Dict[str, Any]:
    """Run the analysis stage for every instrument and assemble the payload."""
    manager = manager or ProviderManager(preferred=config.preferred_provider or None)
    instruments = resolve_instruments(config)

    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_summary": session_summary(),
        "provider_status": manager.availability_report(),
        "timeframes": list(config.timeframes),
        "pairs": [],
    }

    for instrument in instruments:
        logger.info("analysing %s", instrument.pretty)
        payload["pairs"].append(
            analyse_instrument(instrument, manager, config.timeframes, config.bars)
        )

    succeeded = sum(1 for p in payload["pairs"] if not p.get("error"))
    payload["summary"] = {
        "requested": len(instruments),
        "succeeded": succeeded,
        "failed": len(instruments) - succeeded,
    }
    return payload


def write_report(text: str, config: Config, fmt: Optional[str] = None) -> str:
    """Write the report to a timestamped file and return its absolute path."""
    fmt = (fmt or config.report_format).lower()
    extension = "json" if fmt == "json" else "md"

    os.makedirs(config.output_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(config.output_dir, f"forex_{stamp}.{extension}")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)

    return os.path.abspath(path)


def run(
    config: Config,
    dry_run: bool = False,
    push: bool = True,
    manager: Optional[ProviderManager] = None,
) -> Dict[str, Any]:
    """Execute the full pipeline.

    Args:
        config: Runtime configuration.
        dry_run: Skip the LLM call, file write and notifications.
        push: Send notifications when channels are configured.
        manager: Injected provider manager (used by tests).

    Returns:
        A result dict with the payload, rendered text, output path and push status.
    """
    payload = build_payload(config, manager=manager)

    if not dry_run:
        payload["commentary"] = generate_commentary(payload, config.llm)
    else:
        payload["commentary"] = None

    text = report_module.render(payload, config.report_format)

    result: Dict[str, Any] = {
        "payload": payload,
        "report": text,
        "path": None,
        "notifications": {},
    }

    if dry_run:
        return result

    result["path"] = write_report(text, config)

    if push and config.telegram.enabled:
        result["notifications"] = notify(
            report_module.telegram_summary(payload), telegram=config.telegram
        )

    return result
