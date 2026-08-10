"""Technical indicators and structure detection for FX candles.

Everything here is pure: a DataFrame of OHLC goes in, numbers come out. No
network, no configuration, no LLM. That keeps the analysis layer fully testable
against synthetic data, which is how the test suite verifies indicator maths
without depending on a live provider.

Results are expressed in pips wherever a price distance is involved, because a
50-point move means nothing in FX unless you know the pair's pip size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .instruments import Instrument

# Column names expected on every candle frame.
REQUIRED_COLUMNS = ("open", "high", "low", "close")


class InsufficientDataError(ValueError):
    """Raised when a frame has too few candles for the requested calculation."""


def _validate(df: pd.DataFrame, minimum: int) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"candle frame missing columns: {missing}")
    if len(df) < minimum:
        raise InsufficientDataError(
            f"need at least {minimum} candles, got {len(df)}"
        )


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI.

    Uses an exponential mean with ``alpha = 1/period``, which is Wilder's
    smoothing, rather than a simple mean of gains and losses.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # All-gain windows have zero average loss -> RSI is 100 by definition.
    out = out.where(avg_loss != 0.0, 100.0)
    out = out.where(avg_gain != 0.0, out.where(avg_loss == 0.0, 0.0))
    return out


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range using Wilder's smoothing."""
    tr = true_range(df)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    line = fast_ema - slow_ema
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame(
        {"macd": line, "signal": signal_line, "histogram": line - signal_line}
    )


def bollinger(series: pd.Series, period: int = 20, stddev: float = 2.0) -> pd.DataFrame:
    middle = sma(series, period)
    # Population std matches the conventional Bollinger definition.
    sigma = series.rolling(window=period, min_periods=period).std(ddof=0)
    return pd.DataFrame(
        {
            "middle": middle,
            "upper": middle + stddev * sigma,
            "lower": middle - stddev * sigma,
        }
    )


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Rolling high/low channel — the cleanest read on FX range breakouts."""
    return pd.DataFrame(
        {
            "upper": df["high"].rolling(window=period, min_periods=period).max(),
            "lower": df["low"].rolling(window=period, min_periods=period).min(),
        }
    )


def _last_float(series: pd.Series) -> Optional[float]:
    """Last non-NaN value as a plain float, or None if the series is empty/NaN."""
    clean = series.dropna()
    if clean.empty:
        return None
    return float(clean.iloc[-1])


@dataclass
class TrendRead:
    """Directional read from moving-average structure."""

    direction: str  # "up" | "down" | "sideways"
    fast_ma: Optional[float]
    slow_ma: Optional[float]
    separation_pips: Optional[float]
    note: str


@dataclass
class MomentumRead:
    rsi: Optional[float]
    macd_histogram: Optional[float]
    state: str  # "overbought" | "oversold" | "neutral"
    note: str


@dataclass
class VolatilityRead:
    atr_pips: Optional[float]
    atr_percentile: Optional[float]
    regime: str  # "expanding" | "contracting" | "normal" | "unknown"
    note: str


@dataclass
class LevelsRead:
    recent_high: Optional[float]
    recent_low: Optional[float]
    range_pips: Optional[float]
    position_in_range: Optional[float]  # 0.0 at the low, 1.0 at the high
    note: str


@dataclass
class TimeframeAnalysis:
    """Complete read of one timeframe for one instrument."""

    timeframe: str
    candles: int
    last_close: Optional[float]
    change_pips: Optional[float]
    trend: TrendRead
    momentum: MomentumRead
    volatility: VolatilityRead
    levels: LevelsRead
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Flatten for JSON output and LLM prompting."""
        return {
            "timeframe": self.timeframe,
            "candles": self.candles,
            "last_close": self.last_close,
            "change_pips": self.change_pips,
            "trend": {
                "direction": self.trend.direction,
                "fast_ma": self.trend.fast_ma,
                "slow_ma": self.trend.slow_ma,
                "separation_pips": self.trend.separation_pips,
                "note": self.trend.note,
            },
            "momentum": {
                "rsi": self.momentum.rsi,
                "macd_histogram": self.momentum.macd_histogram,
                "state": self.momentum.state,
                "note": self.momentum.note,
            },
            "volatility": {
                "atr_pips": self.volatility.atr_pips,
                "atr_percentile": self.volatility.atr_percentile,
                "regime": self.volatility.regime,
                "note": self.volatility.note,
            },
            "levels": {
                "recent_high": self.levels.recent_high,
                "recent_low": self.levels.recent_low,
                "range_pips": self.levels.range_pips,
                "position_in_range": self.levels.position_in_range,
                "note": self.levels.note,
            },
            "warnings": list(self.warnings),
        }


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(value, digits)


def _analyse_trend(
    df: pd.DataFrame, instrument: Instrument, fast: int, slow: int
) -> TrendRead:
    if len(df) < slow:
        return TrendRead(
            "sideways", None, None, None,
            f"insufficient history for {slow}-period MA",
        )

    fast_ma = _last_float(ema(df["close"], fast))
    slow_ma = _last_float(ema(df["close"], slow))
    if fast_ma is None or slow_ma is None:
        return TrendRead("sideways", fast_ma, slow_ma, None, "moving averages unavailable")

    separation = instrument.pips(fast_ma - slow_ma)
    atr_series = atr(df)
    atr_value = _last_float(atr_series)

    # "Sideways" means the MAs sit closer together than one average candle range,
    # so their ordering is indistinguishable from noise. Empirically the ratio is
    # well under 1 for directionless series and several multiples above it for
    # trending ones, which makes one ATR a clean separator.
    noise_floor_pips = instrument.pips(atr_value) if atr_value else 0.0

    if abs(separation) <= noise_floor_pips:
        direction = "sideways"
        note = "moving averages compressed within noise; no clear trend"
    elif separation > 0:
        direction = "up"
        note = f"fast EMA above slow EMA by {abs(separation):.1f} pips"
    else:
        direction = "down"
        note = f"fast EMA below slow EMA by {abs(separation):.1f} pips"

    return TrendRead(direction, _round(fast_ma, 6), _round(slow_ma, 6), _round(separation, 1), note)


def _analyse_momentum(df: pd.DataFrame, rsi_period: int) -> MomentumRead:
    rsi_value = _last_float(rsi(df["close"], rsi_period)) if len(df) > rsi_period else None
    hist = _last_float(macd(df["close"])["histogram"]) if len(df) >= 35 else None

    if rsi_value is None:
        state, note = "neutral", "insufficient history for RSI"
    elif rsi_value >= 70:
        state, note = "overbought", f"RSI {rsi_value:.1f} in overbought territory"
    elif rsi_value <= 30:
        state, note = "oversold", f"RSI {rsi_value:.1f} in oversold territory"
    else:
        state, note = "neutral", f"RSI {rsi_value:.1f} mid-range"

    if hist is not None:
        note += f"; MACD histogram {'positive' if hist > 0 else 'negative'}"

    return MomentumRead(_round(rsi_value, 1), _round(hist, 6), state, note)


def _analyse_volatility(
    df: pd.DataFrame, instrument: Instrument, period: int
) -> VolatilityRead:
    if len(df) < period + 1:
        return VolatilityRead(None, None, "unknown", "insufficient history for ATR")

    atr_series = atr(df, period).dropna()
    if atr_series.empty:
        return VolatilityRead(None, None, "unknown", "ATR unavailable")

    current = float(atr_series.iloc[-1])
    atr_pips = instrument.pips(current)

    percentile: Optional[float] = None
    regime = "normal"
    if len(atr_series) >= 20:
        percentile = float((atr_series <= current).mean() * 100.0)
        if percentile >= 75:
            regime = "expanding"
        elif percentile <= 25:
            regime = "contracting"

    note = f"ATR {atr_pips:.1f} pips"
    if percentile is not None:
        # Avoid English ordinal suffixes ("21th"); a plain rank reads correctly.
        note += f" (percentile {percentile:.0f} of recent history)"
    if regime == "contracting":
        note += "; compressed ranges often precede breakouts"
    elif regime == "expanding":
        note += "; wide ranges imply wider stops are needed"

    return VolatilityRead(_round(atr_pips, 1), _round(percentile, 0), regime, note)


def _analyse_levels(
    df: pd.DataFrame, instrument: Instrument, period: int
) -> LevelsRead:
    window = df.tail(period)
    if window.empty:
        return LevelsRead(None, None, None, None, "no candles available")

    high = float(window["high"].max())
    low = float(window["low"].min())
    close = float(window["close"].iloc[-1])
    span = high - low

    if span <= 0:
        return LevelsRead(
            _round(high, 6), _round(low, 6), 0.0, None,
            "flat range; levels carry no information",
        )

    position = (close - low) / span
    range_pips = instrument.pips(span)

    if position >= 0.8:
        note = f"price in upper fifth of the {period}-period range ({range_pips:.0f} pips wide)"
    elif position <= 0.2:
        note = f"price in lower fifth of the {period}-period range ({range_pips:.0f} pips wide)"
    else:
        note = f"price mid-range ({range_pips:.0f} pips wide)"

    return LevelsRead(
        _round(high, 6), _round(low, 6), _round(range_pips, 1), _round(position, 3), note
    )


def analyse_timeframe(
    df: pd.DataFrame,
    instrument: Instrument,
    timeframe: str,
    fast_ma: int = 20,
    slow_ma: int = 50,
    rsi_period: int = 14,
    atr_period: int = 14,
    level_period: int = 20,
) -> TimeframeAnalysis:
    """Run the full indicator set over one timeframe.

    Degrades gracefully: a short frame yields ``None`` fields and a warning
    rather than raising, so a provider returning limited history still produces a
    usable (if thinner) report.
    """
    _validate(df, minimum=2)

    df = df.sort_index()
    warnings: List[str] = []

    if len(df) < slow_ma:
        warnings.append(
            f"only {len(df)} candles on {timeframe}; "
            f"trend read needs {slow_ma} and was degraded"
        )

    last_close = float(df["close"].iloc[-1])
    change_pips = instrument.pips(last_close - float(df["close"].iloc[-2]))

    return TimeframeAnalysis(
        timeframe=timeframe,
        candles=len(df),
        last_close=round(last_close, 6),
        change_pips=_round(change_pips, 1),
        trend=_analyse_trend(df, instrument, fast_ma, slow_ma),
        momentum=_analyse_momentum(df, rsi_period),
        volatility=_analyse_volatility(df, instrument, atr_period),
        levels=_analyse_levels(df, instrument, level_period),
        warnings=warnings,
    )


def align_timeframes(reads: Dict[str, TimeframeAnalysis]) -> Dict[str, object]:
    """Summarise agreement across timeframes.

    Multi-timeframe confluence is the single most useful structural signal in
    discretionary FX analysis, so it is computed explicitly instead of being
    left for the model to infer.
    """
    directions = {tf: read.trend.direction for tf, read in reads.items()}
    values = [d for d in directions.values() if d != "sideways"]

    if not values:
        verdict, confidence = "sideways", "low"
    elif all(d == "up" for d in values):
        verdict = "up"
        confidence = "high" if len(values) == len(directions) else "medium"
    elif all(d == "down" for d in values):
        verdict = "down"
        confidence = "high" if len(values) == len(directions) else "medium"
    else:
        verdict, confidence = "conflicted", "low"

    return {
        "per_timeframe": directions,
        "verdict": verdict,
        "confidence": confidence,
        "note": {
            "up": "timeframes agree on an uptrend",
            "down": "timeframes agree on a downtrend",
            "sideways": "no timeframe shows a clear trend",
            "conflicted": "timeframes disagree; treat directional bias as weak",
        }[verdict],
    }
