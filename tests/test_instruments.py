"""Symbol parsing and pip conventions.

Pip size is the foundation of every distance in this codebase, so the JPY and
metal conventions are pinned explicitly rather than assumed to be 0.0001.
"""

from __future__ import annotations

import pytest

from forex.instruments import (
    InvalidSymbolError,
    default_watchlist,
    describe_pip_value,
    is_supported,
    parse_symbol,
    parse_symbols,
)


class TestParseSymbol:
    @pytest.mark.parametrize(
        "raw",
        ["EURUSD", "eurusd", "EUR/USD", "eur/usd", "EUR-USD", "EUR_USD", "EURUSD=X", " EURUSD "],
    )
    def test_accepts_common_spellings(self, raw):
        inst = parse_symbol(raw)
        assert inst.base == "EUR"
        assert inst.quote == "USD"
        assert inst.symbol == "EURUSD"
        assert inst.pretty == "EUR/USD"

    @pytest.mark.parametrize("raw", ["", "   ", None, "EUR", "EURUSDJPY", "XXXYYY", "EUREUR", "123456"])
    def test_rejects_invalid(self, raw):
        with pytest.raises(InvalidSymbolError):
            parse_symbol(raw)

    def test_is_supported_does_not_raise(self):
        assert is_supported("EURUSD") is True
        assert is_supported("NOTAPAIR") is False


class TestPipConventions:
    def test_standard_pair_pip_is_fourth_decimal(self):
        inst = parse_symbol("EURUSD")
        assert inst.pip_size == 0.0001
        assert inst.display_precision == 5

    def test_jpy_pair_pip_is_second_decimal(self):
        """A JPY cross moves in 0.01 increments, not 0.0001."""
        inst = parse_symbol("USDJPY")
        assert inst.pip_size == 0.01
        assert inst.display_precision == 3
        assert inst.is_jpy_cross is True

    def test_gold_uses_metal_convention(self):
        inst = parse_symbol("XAUUSD")
        assert inst.is_metal is True
        assert inst.pip_size == 0.1
        assert inst.display_precision == 2

    def test_pips_conversion_differs_by_pair(self):
        """The same price delta is a very different pip count per convention."""
        eurusd = parse_symbol("EURUSD")
        usdjpy = parse_symbol("USDJPY")

        assert eurusd.pips(0.0010) == pytest.approx(10.0)
        assert usdjpy.pips(0.10) == pytest.approx(10.0)
        # 0.0010 on a JPY pair is a tenth of a pip, not ten pips.
        assert usdjpy.pips(0.0010) == pytest.approx(0.1)

    def test_negative_delta_keeps_sign(self):
        assert parse_symbol("EURUSD").pips(-0.0025) == pytest.approx(-25.0)

    def test_format_price_respects_precision(self):
        assert parse_symbol("EURUSD").format_price(1.23456789) == "1.23457"
        assert parse_symbol("USDJPY").format_price(151.23456) == "151.235"
        assert parse_symbol("XAUUSD").format_price(2345.6789) == "2345.68"

    def test_pip_value_none_for_metals(self):
        """Metal contract sizes vary by broker, so no value is asserted."""
        assert describe_pip_value(parse_symbol("XAUUSD")) is None
        assert describe_pip_value(parse_symbol("EURUSD")) == pytest.approx(10.0)


class TestParseSymbols:
    def test_deduplicates_preserving_order(self):
        out = parse_symbols("EURUSD, eur/usd ,GBPUSD,EURUSD")
        assert [i.symbol for i in out] == ["EURUSD", "GBPUSD"]

    def test_accepts_iterable(self):
        out = parse_symbols(["USDJPY", "XAUUSD"])
        assert [i.symbol for i in out] == ["USDJPY", "XAUUSD"]

    def test_skips_blank_entries(self):
        out = parse_symbols("EURUSD,,  ,GBPUSD")
        assert len(out) == 2

    def test_propagates_invalid_symbol(self):
        with pytest.raises(InvalidSymbolError):
            parse_symbols("EURUSD,NOPE")

    def test_default_watchlist_is_valid_and_nonempty(self):
        watchlist = default_watchlist()
        assert len(watchlist) >= 7
        assert all(i.pip_size > 0 for i in watchlist)
        assert "EURUSD" in [i.symbol for i in watchlist]
