"""Instrument metadata and symbol normalisation for FX pairs and metals.

Equity tickers are opaque identifiers (``AAPL``), but an FX symbol is a *pair* of
currencies whose quoting convention determines what a "pip" is worth and how the
price should be rounded. This module is the single source of truth for that
convention so the rest of the codebase never hardcodes ``0.0001``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

# Metals and other non-currency quote assets that are still quoted FX-style.
_METALS = {
    "XAU": ("Gold", 0.1, 2),
    "XAG": ("Silver", 0.01, 3),
    "XPT": ("Platinum", 0.1, 2),
    "XPD": ("Palladium", 0.1, 2),
}

# Currencies whose small unit makes the pip the 2nd decimal rather than the 4th.
_JPY_LIKE = {"JPY"}

_ISO_CURRENCIES = {
    "AUD", "CAD", "CHF", "CNH", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
    "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "NOK", "NZD", "PLN",
    "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
}

_MAJORS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD")

_SEPARATORS = re.compile(r"[\s/_\-:.]+")


class InvalidSymbolError(ValueError):
    """Raised when a user-supplied symbol cannot be parsed as an FX pair."""


@dataclass(frozen=True)
class Instrument:
    """A single tradable FX pair or metal cross.

    Attributes:
        base: Base currency (the unit being priced), e.g. ``EUR`` in EURUSD.
        quote: Quote currency (the unit doing the pricing), e.g. ``USD``.
        pip_size: Price increment of one pip, used for all pip arithmetic.
        display_precision: Decimal places to use when rendering the price.
    """

    base: str
    quote: str
    pip_size: float
    display_precision: int

    @property
    def symbol(self) -> str:
        """Canonical 6-character form, e.g. ``EURUSD``."""
        return f"{self.base}{self.quote}"

    @property
    def pretty(self) -> str:
        """Human-facing slashed form, e.g. ``EUR/USD``."""
        return f"{self.base}/{self.quote}"

    @property
    def is_metal(self) -> bool:
        return self.base in _METALS

    @property
    def is_jpy_cross(self) -> bool:
        return self.quote in _JPY_LIKE

    def pips(self, price_delta: float) -> float:
        """Convert an absolute price difference into pips."""
        return price_delta / self.pip_size

    def format_price(self, price: float) -> str:
        return f"{price:.{self.display_precision}f}"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.pretty


def _pip_and_precision(base: str, quote: str) -> tuple[float, int]:
    if base in _METALS:
        _, pip, precision = _METALS[base]
        return pip, precision
    if quote in _JPY_LIKE:
        return 0.01, 3
    return 0.0001, 5


def parse_symbol(raw: str) -> Instrument:
    """Parse any common spelling of an FX symbol into an :class:`Instrument`.

    Accepts ``EURUSD``, ``eur/usd``, ``EUR-USD``, ``EUR_USD``, ``EURUSD=X``.

    Raises:
        InvalidSymbolError: If the text is not a recognisable currency pair.
    """
    if raw is None:
        raise InvalidSymbolError("symbol is required")

    text = str(raw).strip().upper()
    if not text:
        raise InvalidSymbolError("symbol is required")

    # Tolerate provider-specific suffixes such as Yahoo's "=X".
    text = text.removesuffix("=X")
    parts = [p for p in _SEPARATORS.split(text) if p]

    if len(parts) == 2:
        base, quote = parts
    elif len(parts) == 1 and len(parts[0]) == 6:
        base, quote = parts[0][:3], parts[0][3:]
    else:
        raise InvalidSymbolError(
            f"cannot parse {raw!r} as an FX pair; expected forms like 'EURUSD' or 'EUR/USD'"
        )

    known = _ISO_CURRENCIES | set(_METALS)
    if base not in known or quote not in _ISO_CURRENCIES:
        raise InvalidSymbolError(
            f"unknown currency in {raw!r}: base={base!r} quote={quote!r}"
        )
    if base == quote:
        raise InvalidSymbolError(f"base and quote are identical in {raw!r}")

    pip, precision = _pip_and_precision(base, quote)
    return Instrument(base=base, quote=quote, pip_size=pip, display_precision=precision)


def parse_symbols(raw: Iterable[str] | str) -> List[Instrument]:
    """Parse a comma-separated string or iterable of symbols, de-duplicated.

    Order is preserved so report output is deterministic.
    """
    if isinstance(raw, str):
        candidates: Iterable[str] = raw.split(",")
    else:
        candidates = raw

    out: List[Instrument] = []
    seen: set[str] = set()
    for item in candidates:
        if not str(item).strip():
            continue
        inst = parse_symbol(item)
        if inst.symbol not in seen:
            seen.add(inst.symbol)
            out.append(inst)
    return out


def default_watchlist() -> List[Instrument]:
    """A conservative default: the liquid majors plus gold."""
    return parse_symbols(list(_MAJORS) + ["XAUUSD"])


def is_supported(raw: str) -> bool:
    try:
        parse_symbol(raw)
    except InvalidSymbolError:
        return False
    return True


def describe_pip_value(instrument: Instrument, lots: float = 1.0) -> Optional[float]:
    """Approximate value of one pip in the quote currency for ``lots`` standard lots.

    A standard lot is 100,000 units of the base currency, so one pip is worth
    ``100_000 * pip_size`` in the *quote* currency. Returns ``None`` for metals,
    whose contract sizes vary by broker and cannot be assumed.
    """
    if instrument.is_metal:
        return None
    return 100_000 * instrument.pip_size * lots
