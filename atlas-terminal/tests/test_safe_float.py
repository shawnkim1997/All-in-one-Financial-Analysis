"""Tests for server.utils.safe_float -- edge cases and boundary conditions."""

import math

import pandas as pd
import pytest

from server.utils.safe_float import _safe_float, _na, _format_shares_display


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    """Exhaustive edge-case coverage for _safe_float."""

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_nan_float_returns_none(self):
        assert _safe_float(float("nan")) is None

    def test_math_nan_returns_none(self):
        assert _safe_float(math.nan) is None

    def test_pandas_na_returns_none(self):
        assert _safe_float(pd.NA) is None

    def test_pandas_nat_returns_none(self):
        assert _safe_float(pd.NaT) is None

    def test_int_converts(self):
        assert _safe_float(42) == 42.0

    def test_float_passthrough(self):
        assert _safe_float(3.14) == 3.14

    def test_negative_float(self):
        assert _safe_float(-9.99) == -9.99

    def test_zero(self):
        assert _safe_float(0) == 0.0

    def test_string_numeric(self):
        assert _safe_float("123.45") == 123.45

    def test_string_negative(self):
        assert _safe_float("-7.5") == -7.5

    def test_string_non_numeric_returns_none(self):
        assert _safe_float("hello") is None

    def test_empty_string_returns_none(self):
        assert _safe_float("") is None

    def test_bool_true(self):
        # bool is subclass of int; float(True) == 1.0
        assert _safe_float(True) == 1.0

    def test_bool_false(self):
        assert _safe_float(False) == 0.0

    def test_inf_positive(self):
        result = _safe_float(float("inf"))
        assert result == float("inf")

    def test_inf_negative(self):
        result = _safe_float(float("-inf"))
        assert result == float("-inf")

    def test_large_number(self):
        assert _safe_float(1e18) == 1e18

    def test_very_small_number(self):
        assert _safe_float(1e-15) == pytest.approx(1e-15)

    def test_object_returns_none(self):
        assert _safe_float(object()) is None

    def test_list_returns_none(self):
        assert _safe_float([1, 2, 3]) is None

    def test_dict_returns_none(self):
        assert _safe_float({"a": 1}) is None


# ---------------------------------------------------------------------------
# _na
# ---------------------------------------------------------------------------

class TestNa:
    """Tests for the _na display helper."""

    def test_none_returns_na_string(self):
        assert _na(None) == "N/A"

    def test_nan_returns_na_string(self):
        assert _na(float("nan")) == "N/A"

    def test_valid_float_passthrough(self):
        assert _na(3.14) == 3.14

    def test_zero_passthrough(self):
        assert _na(0) == 0

    def test_string_passthrough(self):
        assert _na("hello") == "hello"


# ---------------------------------------------------------------------------
# _format_shares_display
# ---------------------------------------------------------------------------

class TestFormatSharesDisplay:
    """Tests for the _format_shares_display utility."""

    def test_none_returns_na(self):
        assert _format_shares_display(None) == "N/A"

    def test_zero_returns_na(self):
        assert _format_shares_display(0) == "N/A"

    def test_negative_returns_na(self):
        assert _format_shares_display(-100) == "N/A"

    def test_billions(self):
        assert _format_shares_display(15_420_000_000) == "15.42B Shares"

    def test_millions(self):
        assert _format_shares_display(1_200_000) == "1.20M Shares"

    def test_thousands(self):
        assert _format_shares_display(5_500) == "5.50K Shares"

    def test_small_number(self):
        assert _format_shares_display(42) == "42 Shares"

    def test_exact_billion(self):
        assert _format_shares_display(1_000_000_000) == "1.00B Shares"

    def test_exact_million(self):
        assert _format_shares_display(1_000_000) == "1.00M Shares"
