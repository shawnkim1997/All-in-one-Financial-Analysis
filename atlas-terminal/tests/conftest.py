"""Shared pytest fixtures for ATLAS Terminal test suite."""

import sys
import asyncio
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so `server.*` imports work.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def sample_ticker():
    """A well-known US ticker for integration-style tests."""
    return "AAPL"


@pytest.fixture(autouse=True)
def isolated_sqlite_db(tmp_path, monkeypatch):
    """Keep tests away from the user's local SQLite database."""
    from server.db import database

    asyncio.run(database.close_db())
    monkeypatch.setattr(database, "_DB_DIR", tmp_path)
    monkeypatch.setattr(database, "_DB_PATH", str(tmp_path / "atlas-test.db"))
    yield
    asyncio.run(database.close_db())


@pytest.fixture
def sample_fcf_inputs():
    """Reasonable DCF inputs for unit-testing valuation functions."""
    return {
        "fcf": 100_000_000_000,       # $100B trailing FCF
        "wacc": 0.10,                  # 10%
        "terminal_growth": 0.025,      # 2.5%
        "fcf_growth": 0.08,            # 8%
        "total_debt": 110_000_000_000, # $110B
        "cash": 60_000_000_000,        # $60B
        "shares": 15_500_000_000,      # 15.5B shares
    }


@pytest.fixture
def sample_balance_sheet_values():
    """Simplified balance-sheet figures for Altman Z / DuPont tests."""
    return {
        "current_assets": 150_000_000_000,
        "current_liabilities": 120_000_000_000,
        "total_assets": 350_000_000_000,
        "retained_earnings": 50_000_000_000,
        "total_liabilities": 290_000_000_000,
        "total_equity": 60_000_000_000,
        "ebit": 120_000_000_000,
        "sales": 400_000_000_000,
        "market_cap": 2_800_000_000_000,
        "net_income": 95_000_000_000,
        "revenue": 400_000_000_000,
    }
