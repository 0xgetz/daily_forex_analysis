"""Pytest fixtures. Shared helpers live in tests/helpers.py."""

from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

# Make the repo root importable so `import forex` and `import main` work
# regardless of how pytest is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers import make_candles  # noqa: E402


@pytest.fixture
def uptrend() -> pd.DataFrame:
    return make_candles(n=200, drift=0.0004, noise=0.0002)


@pytest.fixture
def downtrend() -> pd.DataFrame:
    return make_candles(n=200, drift=-0.0004, noise=0.0002)


@pytest.fixture
def flat() -> pd.DataFrame:
    return make_candles(n=200, drift=0.0, noise=0.00005)
