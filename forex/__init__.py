"""daily_forex_analysis — LLM-assisted technical analysis for spot FX and metals.

Public API:
    Config              runtime configuration from env/.env
    parse_symbol(s)     FX symbol parsing with pip conventions
    ProviderManager     ordered data-provider fallback
    analyse_timeframe   indicator computation for one timeframe
    run                 the full fetch -> analyse -> report pipeline
"""

from .analysis import TimeframeAnalysis, align_timeframes, analyse_timeframe
from .config import Config, LLMConfig, TelegramConfig
from .instruments import (
    Instrument,
    InvalidSymbolError,
    default_watchlist,
    parse_symbol,
    parse_symbols,
)
from .pipeline import build_payload, run
from .providers import CandleSet, ProviderManager
from .sessions import active_sessions, is_market_open, session_summary

__version__ = "0.1.0"

__all__ = [
    "Config",
    "LLMConfig",
    "TelegramConfig",
    "Instrument",
    "InvalidSymbolError",
    "parse_symbol",
    "parse_symbols",
    "default_watchlist",
    "TimeframeAnalysis",
    "analyse_timeframe",
    "align_timeframes",
    "ProviderManager",
    "CandleSet",
    "active_sessions",
    "is_market_open",
    "session_summary",
    "build_payload",
    "run",
    "__version__",
]
