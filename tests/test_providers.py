"""Provider normalisation, fallback ordering and failure isolation.

No test here touches the network: providers are stubbed so the fallback contract
itself is what gets verified.
"""

from __future__ import annotations

import pandas as pd
import pytest

from forex.instruments import parse_symbol
from forex.providers import (
    AllProvidersFailedError,
    AlphaVantageProvider,
    CandleProvider,
    ProviderError,
    ProviderManager,
    TwelveDataProvider,
    YFinanceProvider,
    _normalise,
    build_providers,
    resample,
)

from tests.helpers import StubProvider, make_candles

EURUSD = parse_symbol("EURUSD")


class TestNormalise:
    def test_lowercases_and_selects_columns(self):
        raw = make_candles(n=10).rename(
            columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}
        )
        out = _normalise(raw)
        assert list(out.columns)[:4] == ["open", "high", "low", "close"]

    def test_flattens_multiindex_columns(self):
        """yfinance returns MultiIndex columns even for a single symbol."""
        raw = make_candles(n=10)
        raw.columns = pd.MultiIndex.from_tuples(
            [(c.capitalize(), "EURUSD=X") for c in raw.columns]
        )
        out = _normalise(raw)
        assert "close" in out.columns

    def test_maps_alphavantage_numbered_columns(self):
        raw = pd.DataFrame(
            {
                "1. open": ["1.1", "1.2"],
                "2. high": ["1.3", "1.4"],
                "3. low": ["1.0", "1.1"],
                "4. close": ["1.2", "1.3"],
            },
            index=["2026-01-01", "2026-01-02"],
        )
        out = _normalise(raw)
        assert out["close"].iloc[-1] == pytest.approx(1.3)

    def test_coerces_string_prices_to_float(self):
        raw = make_candles(n=5).astype(str)
        assert _normalise(raw)["close"].dtype.kind == "f"

    def test_sorts_by_index(self):
        raw = make_candles(n=20).iloc[::-1]
        out = _normalise(raw)
        assert out.index.is_monotonic_increasing

    def test_empty_frame_raises(self):
        with pytest.raises(ProviderError):
            _normalise(pd.DataFrame())

    def test_none_raises(self):
        with pytest.raises(ProviderError):
            _normalise(None)

    def test_missing_ohlc_raises(self):
        with pytest.raises(ProviderError, match="missing columns"):
            _normalise(pd.DataFrame({"close": [1.0]}))

    def test_all_nan_prices_raise(self):
        raw = make_candles(n=5)
        raw[["open", "high", "low", "close"]] = None
        with pytest.raises(ProviderError):
            _normalise(raw)


class TestResample:
    def test_hourly_to_four_hourly_reduces_count(self):
        hourly = make_candles(n=48, freq="1h")
        assert len(resample(hourly, "4h")) < len(hourly)

    def test_aggregation_uses_first_open_and_last_close(self):
        hourly = make_candles(n=8, freq="1h")
        out = resample(hourly, "4h")
        assert out["high"].iloc[0] >= out["open"].iloc[0]
        assert out["low"].iloc[0] <= out["close"].iloc[0]

    def test_ohlc_invariants_hold(self):
        out = resample(make_candles(n=100, freq="1h"), "4h")
        assert (out["high"] >= out["low"]).all()
        assert (out["high"] >= out["open"]).all()
        assert (out["high"] >= out["close"]).all()


class TestProviderAvailability:
    def test_yfinance_available_when_installed(self):
        # yfinance is a test dependency, so it must report available here.
        assert YFinanceProvider().is_available() is True

    def test_keyed_providers_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)
        assert AlphaVantageProvider().is_available() is False
        assert TwelveDataProvider().is_available() is False

    def test_keyed_providers_available_with_key(self, monkeypatch):
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "demo")
        monkeypatch.setenv("TWELVEDATA_API_KEY", "demo")
        assert AlphaVantageProvider().is_available() is True
        assert TwelveDataProvider().is_available() is True

    def test_unavailable_reason_is_actionable(self, monkeypatch):
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        assert "ALPHAVANTAGE_API_KEY" in AlphaVantageProvider().unavailable_reason()

    def test_build_providers_honours_preference(self):
        assert build_providers(preferred="yfinance")[0].name == "yfinance"

    def test_build_providers_ignores_unknown_preference(self):
        assert len(build_providers(preferred="nonexistent")) == 3


class TestProviderManagerFallback:
    def test_uses_first_available_provider(self):
        calls = []
        manager = ProviderManager([StubProvider("a", calls=calls), StubProvider("b", calls=calls)])
        result = manager.fetch_candles(EURUSD, ["H1"], bars=50)
        assert result.source == "a"
        assert all(name == "a" for name, _, _ in calls)

    def test_skips_unavailable_provider(self):
        manager = ProviderManager(
            [StubProvider("a", available=False), StubProvider("b")]
        )
        assert manager.fetch_candles(EURUSD, ["H1"], bars=50).source == "b"

    def test_falls_back_when_first_fails(self):
        manager = ProviderManager(
            [StubProvider("a", fail_on=["*"]), StubProvider("b")]
        )
        assert manager.fetch_candles(EURUSD, ["H1", "D1"], bars=50).source == "b"

    def test_provider_must_satisfy_all_timeframes(self):
        """Partial coverage is rejected so one CandleSet never mixes sources."""
        manager = ProviderManager(
            [StubProvider("partial", fail_on=["D1"]), StubProvider("complete")]
        )
        result = manager.fetch_candles(EURUSD, ["H1", "D1"], bars=50)
        assert result.source == "complete"
        assert set(result.frames) == {"H1", "D1"}

    def test_raises_when_all_fail_with_details(self):
        manager = ProviderManager(
            [StubProvider("a", fail_on=["*"]), StubProvider("b", fail_on=["*"])]
        )
        with pytest.raises(AllProvidersFailedError) as exc:
            manager.fetch_candles(EURUSD, ["H1"], bars=50)
        # The message must name both providers so failures are diagnosable.
        assert "a:" in str(exc.value) and "b:" in str(exc.value)

    def test_raises_when_none_configured(self):
        manager = ProviderManager([StubProvider("a", available=False)])
        with pytest.raises(AllProvidersFailedError, match="no data provider is configured"):
            manager.fetch_candles(EURUSD, ["H1"], bars=50)

    def test_availability_report_covers_every_provider(self):
        manager = ProviderManager([StubProvider("a"), StubProvider("b", available=False)])
        report = manager.availability_report()
        assert report["a"] == "available"
        assert "disabled" in report["b"]

    def test_candleset_timeframes_in_canonical_order(self):
        manager = ProviderManager([StubProvider("a")])
        result = manager.fetch_candles(EURUSD, ["D1", "H1"], bars=50)
        assert result.timeframes() == ["H1", "D1"]


class TestAlphaVantageBehaviour:
    def test_metals_rejected_early(self, monkeypatch):
        """Alpha Vantage FX endpoints do not cover XAU, so fail before the call."""
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "demo")
        with pytest.raises(ProviderError, match="metals"):
            AlphaVantageProvider().fetch(parse_symbol("XAUUSD"), "D1", 10)


class TestYFinanceSymbolMapping:
    def test_currency_pair_gets_fx_suffix(self):
        assert YFinanceProvider()._yahoo_symbol(EURUSD) == "EURUSD=X"

    @pytest.mark.parametrize(
        "symbol,expected",
        [("XAUUSD", "GC=F"), ("XAGUSD", "SI=F"), ("XPTUSD", "PL=F"), ("XPDUSD", "PA=F")],
    )
    def test_metals_map_to_futures(self, symbol, expected):
        """Yahoo has no spot metal series, so metals resolve to COMEX futures."""
        assert YFinanceProvider()._yahoo_symbol(parse_symbol(symbol)) == expected

    def test_unsupported_metal_cross_raises_clearly(self):
        with pytest.raises(ProviderError, match="no series"):
            YFinanceProvider()._yahoo_symbol(parse_symbol("XAUEUR"))
