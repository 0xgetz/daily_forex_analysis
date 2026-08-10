"""FX market sessions.

FX trades continuously from Sunday 21:00 UTC to Friday 21:00 UTC, so the
equity notion of a "trading day" with an open and close does not apply. What
matters instead is *which session is active*: liquidity and typical range differ
sharply between the Tokyo, London and New York windows, and the London/New York
overlap is the highest-volume part of the day.

All times are UTC and deliberately approximate — they describe liquidity
regimes, not exchange rules, and are not adjusted for regional DST.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import List, Optional


@dataclass(frozen=True)
class Session:
    name: str
    start_hour: int
    end_hour: int
    description: str

    def contains(self, moment: datetime) -> bool:
        """Whether ``moment`` (any tz-aware datetime) falls inside this session."""
        hour = _as_utc(moment).hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        # Wraps past midnight UTC (e.g. Sydney 21:00 -> 06:00).
        return hour >= self.start_hour or hour < self.end_hour


SYDNEY = Session("Sydney", 21, 6, "Thin liquidity; ranges often narrow")
TOKYO = Session("Tokyo", 0, 9, "JPY and AUD flows dominate")
LONDON = Session("London", 7, 16, "Highest FX volume; EUR and GBP flows")
NEW_YORK = Session("New York", 12, 21, "USD data releases; London overlap 12:00-16:00")

SESSIONS: tuple[Session, ...] = (SYDNEY, TOKYO, LONDON, NEW_YORK)

# The London/New York overlap, when most of the daily range is typically set.
OVERLAP_START_HOUR = 12
OVERLAP_END_HOUR = 16

_MARKET_OPEN_WEEKDAY = 6   # Sunday
_MARKET_CLOSE_WEEKDAY = 4  # Friday
_MARKET_BOUNDARY_HOUR = 21


def _as_utc(moment: datetime) -> datetime:
    """Normalise to UTC, treating naive input as already-UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def active_sessions(moment: Optional[datetime] = None) -> List[Session]:
    """Sessions currently open. Empty when the market is closed for the weekend."""
    moment = _as_utc(moment or datetime.now(timezone.utc))
    if not is_market_open(moment):
        return []
    return [s for s in SESSIONS if s.contains(moment)]


def is_market_open(moment: Optional[datetime] = None) -> bool:
    """Whether the spot FX market is open.

    Open: Sunday 21:00 UTC through Friday 21:00 UTC.
    """
    moment = _as_utc(moment or datetime.now(timezone.utc))
    weekday = moment.weekday()  # Monday=0 .. Sunday=6

    if weekday == _MARKET_CLOSE_WEEKDAY:  # Friday
        return moment.hour < _MARKET_BOUNDARY_HOUR
    if weekday == 5:  # Saturday
        return False
    if weekday == _MARKET_OPEN_WEEKDAY:  # Sunday
        return moment.hour >= _MARKET_BOUNDARY_HOUR
    return True


def in_london_new_york_overlap(moment: Optional[datetime] = None) -> bool:
    """Whether we are in the highest-liquidity window of the day."""
    moment = _as_utc(moment or datetime.now(timezone.utc))
    if not is_market_open(moment):
        return False
    return OVERLAP_START_HOUR <= moment.hour < OVERLAP_END_HOUR


def session_summary(moment: Optional[datetime] = None) -> str:
    """One-line description of the current session state, for reports and prompts."""
    moment = _as_utc(moment or datetime.now(timezone.utc))
    if not is_market_open(moment):
        return "Market closed (weekend); spot FX reopens Sunday 21:00 UTC"

    names = [s.name for s in active_sessions(moment)]
    if not names:
        return "Between sessions; liquidity thin"

    text = " + ".join(names)
    if in_london_new_york_overlap(moment):
        return f"{text} (London/New York overlap - peak liquidity)"
    return text


def relevant_sessions_for(base: str, quote: str) -> List[Session]:
    """Sessions whose flows most affect a given pair.

    Used to tell the model *when* a pair is likely to move, rather than implying
    every pair trades uniformly around the clock.
    """
    currencies = {base.upper(), quote.upper()}
    out: List[Session] = []
    if currencies & {"JPY", "AUD", "NZD", "CNH", "SGD", "HKD"}:
        out.append(TOKYO)
    if currencies & {"EUR", "GBP", "CHF", "SEK", "NOK", "PLN", "CZK", "HUF", "TRY", "ZAR"}:
        out.append(LONDON)
    if currencies & {"USD", "CAD", "MXN"}:
        out.append(NEW_YORK)
    if currencies & {"AUD", "NZD"}:
        out.append(SYDNEY)

    # Metals track USD flows most closely.
    if base.upper().startswith("X") and NEW_YORK not in out:
        out.append(NEW_YORK)

    if not out:
        out.append(LONDON)

    # Preserve canonical ordering for deterministic output.
    return [s for s in SESSIONS if s in out]
