"""Shared test helpers: synthetic candles and stub providers.

Kept in a plain module (not conftest) so test files can import it directly
without relative-import gymnastics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex.providers import CandleProvider, ProviderError


def make_candles(
    n: int = 200,
    start: float = 1.1000,
    drift: float = 0.0,
    noise: float = 0.0005,
    freq: str = "1h",
    seed: int = 7,
) -> pd.DataFrame:
    """Build a deterministic OHLC frame.

    Args:
        n: Number of candles.
        start: Opening price of the first candle.
        drift: Per-candle directional drift; positive trends up.
        noise: Scale of the random component.
        freq: Pandas offset alias for the index.
        seed: RNG seed, so every run produces identical data.
    """
    rng = np.random.default_rng(seed)
    steps = drift + rng.normal(0.0, noise, size=n)
    close = start + np.cumsum(steps)

    open_ = np.concatenate([[start], close[:-1]])
    spread = np.abs(rng.normal(0.0, noise, size=n)) + noise / 2
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread

    index = pd.date_range("2026-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1000.0},
        index=index,
    )


class StubProvider(CandleProvider):
    """Configurable stand-in for a real provider; never touches the network."""

    def __init__(self, name, available=True, fail_on=None, calls=None):
        self.name = name
        self._available = available
        self._fail_on = set(fail_on or ())
        self.calls = calls if calls is not None else []

    def is_available(self):
        return self._available

    def unavailable_reason(self):
        return f"{self.name} disabled for test"

    def fetch(self, instrument, timeframe, bars):
        self.calls.append((self.name, instrument.symbol, timeframe))
        if timeframe in self._fail_on or "*" in self._fail_on:
            raise ProviderError(f"{self.name} cannot serve {timeframe}")
        return make_candles(n=bars, seed=len(self.name))
