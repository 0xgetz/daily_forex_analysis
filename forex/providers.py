"""Market data providers with ordered fallback.

Every provider is optional and self-declaring: it reports whether it is usable
(dependency installed, API key present) so the manager can skip it silently
instead of failing the whole run. Anyone can therefore clone this repo and run it
with whichever data source *they* have credentials for.

Adding a provider means subclassing :class:`CandleProvider` and appending it to
``build_providers``. No other module needs to change.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .instruments import Instrument

logger = logging.getLogger(__name__)

# Canonical timeframe names mapped to each provider's own vocabulary.
TIMEFRAMES = ("H1", "H4", "D1")


class ProviderError(RuntimeError):
    """A provider failed to return usable data."""


class AllProvidersFailedError(RuntimeError):
    """Every configured provider failed for a symbol."""


@dataclass
class CandleSet:
    """Candles for one instrument across several timeframes."""

    instrument: Instrument
    frames: Dict[str, pd.DataFrame]
    source: str

    def timeframes(self) -> List[str]:
        return [tf for tf in TIMEFRAMES if tf in self.frames]


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce any provider's frame into lowercase OHLC with a sorted DatetimeIndex."""
    if df is None or len(df) == 0:
        raise ProviderError("provider returned no rows")

    out = df.copy()

    # Flatten the MultiIndex columns yfinance returns for single-symbol requests.
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            str(level[0]) if isinstance(level, tuple) else str(level)
            for level in out.columns
        ]

    # Alpha Vantage prefixes fields with an ordinal ("1. open"); strip it before
    # normalising whitespace, otherwise "1. open" becomes "1._open".
    out.columns = [
        re.sub(r"^\d+\.\s*", "", str(c).strip()).lower().replace(" ", "_")
        for c in out.columns
    ]

    rename = {
        "adj_close": "close",
        "price": "close",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})

    # Drop duplicate labels (e.g. both "close" and "adj_close" mapping to "close").
    out = out.loc[:, ~out.columns.duplicated()]

    required = ("open", "high", "low", "close")
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ProviderError(f"provider frame missing columns {missing}")

    out = out[[*required] + (["volume"] if "volume" in out.columns else [])]

    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True, errors="coerce")
    out = out[~out.index.isna()]

    for col in required:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=list(required)).sort_index()
    if out.empty:
        raise ProviderError("provider frame empty after cleaning")
    return out


class CandleProvider(ABC):
    """Base class for a source of OHLC candles."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can be used in the current environment."""

    @abstractmethod
    def fetch(self, instrument: Instrument, timeframe: str, bars: int) -> pd.DataFrame:
        """Return at most ``bars`` candles, oldest first. Raise ProviderError on failure."""

    def unavailable_reason(self) -> str:
        return "not configured"


class YFinanceProvider(CandleProvider):
    """Yahoo Finance via the ``yfinance`` package. No API key required."""

    name = "yfinance"

    _INTERVALS = {"H1": "1h", "H4": "1h", "D1": "1d"}
    _PERIODS = {"H1": "1mo", "H4": "3mo", "D1": "2y"}

    # Yahoo has no spot metal quote (``XAUUSD=X`` returns nothing), so metals are
    # served from the COMEX futures front month instead. Futures carry basis and
    # roll effects, so the level differs slightly from a broker's spot price —
    # acceptable for technical structure, not for execution.
    _METAL_SYMBOLS = {
        "XAUUSD": "GC=F",
        "XAGUSD": "SI=F",
        "XPTUSD": "PL=F",
        "XPDUSD": "PA=F",
    }

    def is_available(self) -> bool:
        try:
            import yfinance  # noqa: F401
        except ImportError:
            return False
        return True

    def unavailable_reason(self) -> str:
        return "yfinance package not installed (pip install yfinance)"

    def _yahoo_symbol(self, instrument: Instrument) -> str:
        if instrument.symbol in self._METAL_SYMBOLS:
            return self._METAL_SYMBOLS[instrument.symbol]
        if instrument.is_metal:
            raise ProviderError(
                f"yfinance has no series for {instrument.pretty}; "
                "supported metals are XAU/XAG/XPT/XPD against USD"
            )
        return f"{instrument.symbol}=X"

    def fetch(self, instrument: Instrument, timeframe: str, bars: int) -> pd.DataFrame:
        import yfinance as yf

        interval = self._INTERVALS.get(timeframe)
        if interval is None:
            raise ProviderError(f"unsupported timeframe {timeframe}")

        try:
            raw = yf.download(
                self._yahoo_symbol(instrument),
                period=self._PERIODS[timeframe],
                interval=interval,
                progress=False,
                auto_adjust=False,
            )
        except Exception as exc:  # network, parsing, rate limits
            raise ProviderError(f"yfinance request failed: {exc}") from exc

        frame = _normalise(raw)

        # Yahoo has no native 4-hour bar, so resample the hourly series.
        if timeframe == "H4":
            frame = resample(frame, "4h")

        return frame.tail(bars)


class AlphaVantageProvider(CandleProvider):
    """Alpha Vantage FX endpoints. Requires a free ``ALPHAVANTAGE_API_KEY``."""

    name = "alphavantage"
    _BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 20):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY") or ""
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def unavailable_reason(self) -> str:
        return "ALPHAVANTAGE_API_KEY not set"

    def fetch(self, instrument: Instrument, timeframe: str, bars: int) -> pd.DataFrame:
        import requests

        if instrument.is_metal:
            raise ProviderError("Alpha Vantage FX endpoints do not cover metals")

        if timeframe == "D1":
            params = {
                "function": "FX_DAILY",
                "from_symbol": instrument.base,
                "to_symbol": instrument.quote,
                "outputsize": "full",
                "apikey": self.api_key,
            }
            key = "Time Series FX (Daily)"
        else:
            params = {
                "function": "FX_INTRADAY",
                "from_symbol": instrument.base,
                "to_symbol": instrument.quote,
                "interval": "60min",
                "outputsize": "full",
                "apikey": self.api_key,
            }
            key = "Time Series FX (60min)"

        try:
            response = requests.get(self._BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ProviderError(f"Alpha Vantage request failed: {exc}") from exc

        # The API signals problems with a 200 status and an explanatory body.
        for field in ("Note", "Information", "Error Message"):
            if field in payload:
                raise ProviderError(f"Alpha Vantage: {payload[field]}")

        series = payload.get(key)
        if not series:
            raise ProviderError(f"Alpha Vantage response missing {key!r}")

        frame = _normalise(pd.DataFrame.from_dict(series, orient="index"))

        if timeframe == "H4":
            frame = resample(frame, "4h")

        return frame.tail(bars)


class TwelveDataProvider(CandleProvider):
    """Twelve Data time-series endpoint. Requires ``TWELVEDATA_API_KEY``."""

    name = "twelvedata"
    _BASE_URL = "https://api.twelvedata.com/time_series"
    _INTERVALS = {"H1": "1h", "H4": "4h", "D1": "1day"}

    def __init__(self, api_key: Optional[str] = None, timeout: int = 20):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY") or ""
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def unavailable_reason(self) -> str:
        return "TWELVEDATA_API_KEY not set"

    def fetch(self, instrument: Instrument, timeframe: str, bars: int) -> pd.DataFrame:
        import requests

        interval = self._INTERVALS.get(timeframe)
        if interval is None:
            raise ProviderError(f"unsupported timeframe {timeframe}")

        params = {
            "symbol": instrument.pretty,
            "interval": interval,
            "outputsize": str(max(bars, 100)),
            "apikey": self.api_key,
            "format": "JSON",
        }

        try:
            response = requests.get(self._BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ProviderError(f"Twelve Data request failed: {exc}") from exc

        if str(payload.get("status")).lower() == "error":
            raise ProviderError(f"Twelve Data: {payload.get('message')}")

        values = payload.get("values")
        if not values:
            raise ProviderError("Twelve Data response contained no values")

        frame = pd.DataFrame(values)
        if "datetime" in frame.columns:
            frame = frame.set_index("datetime")

        return _normalise(frame).tail(bars)


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate candles to a coarser timeframe (e.g. hourly to 4-hourly)."""
    agg: Dict[str, str] = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    }
    if "volume" in df.columns:
        agg["volume"] = "sum"

    out = df.resample(rule, label="right", closed="right").agg(agg).dropna(how="any")
    if out.empty:
        raise ProviderError(f"resampling to {rule} produced no candles")
    return out


def build_providers(preferred: Optional[str] = None) -> List[CandleProvider]:
    """Instantiate all providers in fallback order.

    Args:
        preferred: Optional provider name to try first.
    """
    providers: List[CandleProvider] = [
        TwelveDataProvider(),
        AlphaVantageProvider(),
        YFinanceProvider(),
    ]

    if preferred:
        wanted = preferred.strip().lower()
        providers.sort(key=lambda p: 0 if p.name == wanted else 1)

    return providers


class ProviderManager:
    """Tries each available provider in order until one returns usable candles."""

    def __init__(self, providers: Optional[List[CandleProvider]] = None, preferred: Optional[str] = None):
        self.providers = providers if providers is not None else build_providers(preferred)

    def available(self) -> List[CandleProvider]:
        return [p for p in self.providers if p.is_available()]

    def availability_report(self) -> Dict[str, str]:
        """Per-provider status, so users can see why a source was skipped."""
        return {
            p.name: ("available" if p.is_available() else p.unavailable_reason())
            for p in self.providers
        }

    def fetch_candles(
        self,
        instrument: Instrument,
        timeframes: Optional[List[str]] = None,
        bars: int = 300,
    ) -> CandleSet:
        """Fetch every timeframe for one instrument from the first working provider.

        A provider must satisfy *all* requested timeframes to be accepted, so a
        single CandleSet never mixes sources with different conventions.
        """
        timeframes = list(timeframes or TIMEFRAMES)
        usable = self.available()

        if not usable:
            detail = "; ".join(f"{k}: {v}" for k, v in self.availability_report().items())
            raise AllProvidersFailedError(f"no data provider is configured ({detail})")

        errors: List[str] = []
        for provider in usable:
            frames: Dict[str, pd.DataFrame] = {}
            try:
                for timeframe in timeframes:
                    frames[timeframe] = provider.fetch(instrument, timeframe, bars)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning(
                    "provider %s failed for %s: %s", provider.name, instrument.symbol, exc
                )
                continue

            return CandleSet(instrument=instrument, frames=frames, source=provider.name)

        raise AllProvidersFailedError(
            f"all providers failed for {instrument.symbol}: " + " | ".join(errors)
        )
