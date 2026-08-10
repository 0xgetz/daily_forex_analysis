"""FX session logic.

These tests pin the 24/5 weekend boundary, which is the main structural
difference from an equity market's daily open/close.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from forex.sessions import (
    LONDON,
    NEW_YORK,
    TOKYO,
    active_sessions,
    in_london_new_york_overlap,
    is_market_open,
    relevant_sessions_for,
    session_summary,
)


def utc(year, month, day, hour):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


class TestMarketOpen:
    def test_open_midweek(self):
        # Wednesday 2026-08-12, 10:00 UTC
        assert is_market_open(utc(2026, 8, 12, 10)) is True

    def test_closed_saturday(self):
        assert is_market_open(utc(2026, 8, 15, 12)) is False

    def test_friday_closes_at_21_utc(self):
        assert is_market_open(utc(2026, 8, 14, 20)) is True
        assert is_market_open(utc(2026, 8, 14, 21)) is False

    def test_sunday_opens_at_21_utc(self):
        assert is_market_open(utc(2026, 8, 16, 20)) is False
        assert is_market_open(utc(2026, 8, 16, 21)) is True

    def test_naive_datetime_treated_as_utc(self):
        """Naive input must not raise; it is interpreted as UTC."""
        assert is_market_open(datetime(2026, 8, 12, 10)) is True


class TestActiveSessions:
    def test_weekend_has_no_active_sessions(self):
        assert active_sessions(utc(2026, 8, 15, 12)) == []

    def test_london_active_midmorning(self):
        names = [s.name for s in active_sessions(utc(2026, 8, 12, 9))]
        assert "London" in names

    def test_tokyo_active_early(self):
        names = [s.name for s in active_sessions(utc(2026, 8, 12, 2))]
        assert "Tokyo" in names

    def test_overlap_lists_both_london_and_new_york(self):
        names = [s.name for s in active_sessions(utc(2026, 8, 12, 14))]
        assert "London" in names and "New York" in names

    def test_sydney_session_wraps_midnight(self):
        """Sydney runs 21:00-06:00 UTC, so it must match on both sides."""
        assert SYDNEY_contains(utc(2026, 8, 12, 23))
        assert SYDNEY_contains(utc(2026, 8, 12, 3))
        assert not SYDNEY_contains(utc(2026, 8, 12, 12))


def SYDNEY_contains(moment):
    from forex.sessions import SYDNEY

    return SYDNEY.contains(moment)


class TestOverlap:
    @pytest.mark.parametrize("hour,expected", [(11, False), (12, True), (15, True), (16, False)])
    def test_overlap_window(self, hour, expected):
        assert in_london_new_york_overlap(utc(2026, 8, 12, hour)) is expected

    def test_no_overlap_on_weekend(self):
        assert in_london_new_york_overlap(utc(2026, 8, 15, 14)) is False


class TestSummary:
    def test_weekend_summary_mentions_closed(self):
        text = session_summary(utc(2026, 8, 15, 12))
        assert "closed" in text.lower()

    def test_overlap_summary_mentions_peak_liquidity(self):
        text = session_summary(utc(2026, 8, 12, 14))
        assert "overlap" in text.lower()

    def test_summary_is_never_empty(self):
        for hour in range(24):
            assert session_summary(utc(2026, 8, 12, hour)).strip()


class TestRelevantSessions:
    def test_jpy_pair_maps_to_tokyo(self):
        assert TOKYO in relevant_sessions_for("USD", "JPY")

    def test_eur_pair_maps_to_london(self):
        assert LONDON in relevant_sessions_for("EUR", "USD")

    def test_usd_pair_maps_to_new_york(self):
        assert NEW_YORK in relevant_sessions_for("EUR", "USD")

    def test_gold_maps_to_new_york(self):
        assert NEW_YORK in relevant_sessions_for("XAU", "USD")

    def test_always_returns_something(self):
        assert relevant_sessions_for("CZK", "PLN")

    def test_ordering_is_canonical(self):
        """Output order must be stable for deterministic reports."""
        first = relevant_sessions_for("AUD", "JPY")
        second = relevant_sessions_for("AUD", "JPY")
        assert [s.name for s in first] == [s.name for s in second]
