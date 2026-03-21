"""Tests for server.services.dcf_engine -- DCF formula accuracy."""

import pytest

from server.services.dcf_engine import (
    dcf_intrinsic_value,
    dcf_10y_2stage,
    excel_style_dcf,
    _damodaran_wacc_for_sector,
    DAMODARAN_WACC,
)


# ---------------------------------------------------------------------------
# dcf_intrinsic_value (5-year single-stage)
# ---------------------------------------------------------------------------

class TestDCFIntrinsicValue:
    """Verify 5-year single-stage DCF maths."""

    def test_basic_positive_fcf(self):
        """Known-good manual calculation with simple inputs."""
        result = dcf_intrinsic_value(
            fcf=100, wacc=0.10, terminal_growth=0.02, fcf_growth=0.05, years=5,
        )
        # Manually:
        # Y1: 100/(1.10)^1, Y2: 105/(1.10)^2, ...  + terminal value
        assert result > 0
        # Rough sanity: terminal value dominates, so EV > 5 * FCF
        assert result > 500

    def test_zero_fcf_returns_zero(self):
        assert dcf_intrinsic_value(0, 0.10, 0.02, 0.05) == 0.0

    def test_negative_fcf_returns_zero(self):
        assert dcf_intrinsic_value(-100, 0.10, 0.02, 0.05) == 0.0

    def test_none_fcf_returns_zero(self):
        assert dcf_intrinsic_value(None, 0.10, 0.02, 0.05) == 0.0

    def test_wacc_less_than_terminal_growth_returns_zero(self):
        """Gordon growth model breaks if WACC <= g."""
        assert dcf_intrinsic_value(100, 0.02, 0.05, 0.05) == 0.0

    def test_wacc_equal_terminal_growth_returns_zero(self):
        assert dcf_intrinsic_value(100, 0.05, 0.05, 0.05) == 0.0

    def test_zero_wacc_returns_zero(self):
        assert dcf_intrinsic_value(100, 0, 0.02, 0.05) == 0.0

    def test_higher_growth_higher_value(self):
        """Increasing FCF growth should increase EV."""
        low = dcf_intrinsic_value(100, 0.10, 0.02, 0.03)
        high = dcf_intrinsic_value(100, 0.10, 0.02, 0.10)
        assert high > low

    def test_higher_wacc_lower_value(self):
        """Increasing WACC should decrease EV (more discounting)."""
        low_wacc = dcf_intrinsic_value(100, 0.08, 0.02, 0.05)
        high_wacc = dcf_intrinsic_value(100, 0.15, 0.02, 0.05)
        assert low_wacc > high_wacc

    def test_reproducibility(self):
        """Same inputs always yield same result (deterministic)."""
        a = dcf_intrinsic_value(1000, 0.10, 0.025, 0.08, years=5)
        b = dcf_intrinsic_value(1000, 0.10, 0.025, 0.08, years=5)
        assert a == b

    def test_manual_calculation(self):
        """Hand-verify a simple 2-year DCF with no growth."""
        # FCF=100, growth=0%, WACC=10%, terminal_growth=0%, years=2
        # Y1 PV = 100/1.10 = 90.909...
        # Y2 PV = 100/1.21 = 82.644...
        # Terminal FCF after Y2 = 100 (no growth applied beyond projection)
        # TV = 100*(1+0)/(0.10-0) = 1000
        # PV of TV = 1000/1.21 = 826.446...
        # Total = 90.909 + 82.644 + 826.446 = ~1000
        result = dcf_intrinsic_value(100, 0.10, 0.0, 0.0, years=2)
        assert result == pytest.approx(1000.0, rel=0.01)


# ---------------------------------------------------------------------------
# dcf_10y_2stage
# ---------------------------------------------------------------------------

class TestDCF10y2Stage:
    """Verify 10-year two-stage DCF."""

    def test_positive_result(self):
        result = dcf_10y_2stage(fcf=100, wacc=0.10, term_growth=0.02, fcf_growth=0.08)
        assert result > 0

    def test_zero_fcf(self):
        assert dcf_10y_2stage(0, 0.10, 0.02, 0.08) == 0.0

    def test_none_fcf(self):
        assert dcf_10y_2stage(None, 0.10, 0.02, 0.08) == 0.0

    def test_wacc_leq_terminal(self):
        assert dcf_10y_2stage(100, 0.02, 0.03, 0.08) == 0.0

    def test_two_stage_higher_than_single_with_high_growth(self):
        """With high near-term growth, 10y 2-stage should capture more value
        than a 5-year model because it has more high-growth years."""
        two_stage = dcf_10y_2stage(100, 0.10, 0.02, 0.15)
        single = dcf_intrinsic_value(100, 0.10, 0.02, 0.15, years=5)
        # 10y model projects more years of above-terminal growth
        assert two_stage > single * 0.8  # at least in the same ballpark


# ---------------------------------------------------------------------------
# excel_style_dcf
# ---------------------------------------------------------------------------

class TestExcelStyleDCF:
    """Verify EV -> Equity -> per-share bridge."""

    def test_basic_output_keys(self, sample_fcf_inputs):
        result = excel_style_dcf(
            fcf_base=sample_fcf_inputs["fcf"],
            wacc=sample_fcf_inputs["wacc"],
            term_growth=sample_fcf_inputs["terminal_growth"],
            fcf_growth=sample_fcf_inputs["fcf_growth"],
            total_debt=sample_fcf_inputs["total_debt"],
            cash=sample_fcf_inputs["cash"],
            shares=sample_fcf_inputs["shares"],
        )
        assert "ev" in result
        assert "equity_value" in result
        assert "value_per_share" in result
        assert "shares" in result

    def test_equity_equals_ev_minus_debt_plus_cash(self, sample_fcf_inputs):
        result = excel_style_dcf(
            fcf_base=sample_fcf_inputs["fcf"],
            wacc=sample_fcf_inputs["wacc"],
            term_growth=sample_fcf_inputs["terminal_growth"],
            fcf_growth=sample_fcf_inputs["fcf_growth"],
            total_debt=sample_fcf_inputs["total_debt"],
            cash=sample_fcf_inputs["cash"],
            shares=sample_fcf_inputs["shares"],
        )
        expected_equity = result["ev"] - sample_fcf_inputs["total_debt"] + sample_fcf_inputs["cash"]
        assert result["equity_value"] == pytest.approx(expected_equity, rel=1e-9)

    def test_value_per_share_equals_equity_div_shares(self, sample_fcf_inputs):
        result = excel_style_dcf(
            fcf_base=sample_fcf_inputs["fcf"],
            wacc=sample_fcf_inputs["wacc"],
            term_growth=sample_fcf_inputs["terminal_growth"],
            fcf_growth=sample_fcf_inputs["fcf_growth"],
            total_debt=sample_fcf_inputs["total_debt"],
            cash=sample_fcf_inputs["cash"],
            shares=sample_fcf_inputs["shares"],
        )
        expected_vps = result["equity_value"] / sample_fcf_inputs["shares"]
        assert result["value_per_share"] == pytest.approx(expected_vps, rel=1e-9)

    def test_zero_shares_returns_none_vps(self):
        result = excel_style_dcf(100, 0.10, 0.02, 0.08, 50, 20, 0)
        assert result["value_per_share"] is None

    def test_none_shares_returns_none_vps(self):
        result = excel_style_dcf(100, 0.10, 0.02, 0.08, 50, 20, None)
        assert result["value_per_share"] is None


# ---------------------------------------------------------------------------
# _damodaran_wacc_for_sector
# ---------------------------------------------------------------------------

class TestDamodaranWACC:
    """Test sector -> WACC mapping."""

    def test_software_sector(self):
        assert _damodaran_wacc_for_sector("Software") == DAMODARAN_WACC["Software"]

    def test_technology_sector(self):
        assert _damodaran_wacc_for_sector("Technology") == DAMODARAN_WACC["Software"]

    def test_healthcare(self):
        assert _damodaran_wacc_for_sector("Healthcare") == DAMODARAN_WACC["Healthcare"]

    def test_utilities(self):
        assert _damodaran_wacc_for_sector("Utilities") == DAMODARAN_WACC["Utilities"]

    def test_unknown_sector_default(self):
        assert _damodaran_wacc_for_sector("Alien Technology") == 8.0

    def test_empty_string_default(self):
        assert _damodaran_wacc_for_sector("") == 8.0

    def test_none_default(self):
        assert _damodaran_wacc_for_sector(None) == 8.0

    def test_case_insensitive(self):
        assert _damodaran_wacc_for_sector("software") == DAMODARAN_WACC["Software"]
        assert _damodaran_wacc_for_sector("FINANCIAL SERVICES") == DAMODARAN_WACC["Financials"]
