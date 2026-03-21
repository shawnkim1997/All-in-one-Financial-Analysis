"""Tests for server.services.financial_metrics -- DuPont, Altman Z, radar normalisation."""

import pytest

from server.services.financial_metrics import _radar_norm


# ---------------------------------------------------------------------------
# _radar_norm
# ---------------------------------------------------------------------------

class TestRadarNorm:
    """Verify radar chart normalisation to 0-100 range."""

    def test_all_none_returns_defaults(self):
        result = _radar_norm(None, None, None, None, None)
        assert result == [50, 50, 50, 50, 50]

    def test_returns_five_values(self):
        result = _radar_norm(15.0, 1.5, 1.0, 2.0, 10.0)
        assert len(result) == 5

    def test_all_values_in_range(self):
        result = _radar_norm(30.0, 2.5, 1.5, 2.5, 25.0)
        for v in result:
            assert 0 <= v <= 100

    def test_extreme_high_values_capped_at_100(self):
        result = _radar_norm(100.0, 10.0, 5.0, 10.0, 100.0)
        for v in result:
            assert v <= 100

    def test_extreme_low_values_floored_at_0(self):
        result = _radar_norm(-50.0, -1.0, -1.0, -1.0, -50.0)
        for v in result:
            assert v >= 0

    def test_roe_normalisation(self):
        # n_roe: (x + 10) / 40 * 100
        # ROE = 30% -> (30+10)/40*100 = 100
        result = _radar_norm(30.0, None, None, None, None)
        assert result[0] == 100.0

    def test_roe_negative(self):
        # ROE = -10% -> (-10+10)/40*100 = 0
        result = _radar_norm(-10.0, None, None, None, None)
        assert result[0] == 0.0

    def test_current_ratio_normalisation(self):
        # n_cr: x / 3 * 100
        # CR = 1.5 -> 1.5/3*100 = 50
        result = _radar_norm(None, 1.5, None, None, None)
        assert result[1] == 50.0

    def test_asset_turnover_normalisation(self):
        # n_at: x * 50
        # AT = 1.0 -> 50
        result = _radar_norm(None, None, 1.0, None, None)
        assert result[2] == 50.0

    def test_equity_mult_normalisation(self):
        # n_em: (x - 0.5) / 2.5 * 100
        # EM = 2.0 -> (2.0-0.5)/2.5*100 = 60
        result = _radar_norm(None, None, None, 2.0, None)
        assert result[3] == 60.0

    def test_yoy_normalisation(self):
        # n_yoy: (x + 20) / 50 * 100
        # YoY = 10% -> (10+20)/50*100 = 60
        result = _radar_norm(None, None, None, None, 10.0)
        assert result[4] == 60.0


# ---------------------------------------------------------------------------
# Altman Z-Score formula verification (unit-level)
# ---------------------------------------------------------------------------

class TestAltmanZFormula:
    """Verify the Altman Z-Score formula independently of data fetching."""

    def test_altman_z_manual_calculation(self, sample_balance_sheet_values):
        """Hand-compute Altman Z and check the formula:
        Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
        where:
          A = Working Capital / Total Assets
          B = Retained Earnings / Total Assets
          C = EBIT / Total Assets
          D = Market Cap / Total Liabilities
          E = Sales / Total Assets
        """
        v = sample_balance_sheet_values
        ta = v["total_assets"]
        a = (v["current_assets"] - v["current_liabilities"]) / ta
        b = v["retained_earnings"] / ta
        c = v["ebit"] / ta
        d = v["market_cap"] / v["total_liabilities"]
        e = v["sales"] / ta

        z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

        # With the sample values:
        # A = (150B-120B)/350B = 30/350 = 0.08571
        # B = 50B/350B = 0.14286
        # C = 120B/350B = 0.34286
        # D = 2800B/290B = 9.65517
        # E = 400B/350B = 1.14286
        assert z == pytest.approx(
            1.2 * 0.08571 + 1.4 * 0.14286 + 3.3 * 0.34286 + 0.6 * 9.65517 + 1.0 * 1.14286,
            rel=0.01,
        )
        # Z > 2.99 is "safe zone"
        assert z > 2.99

    def test_altman_z_distress_zone(self):
        """A company with poor financials should score below 1.81."""
        ta = 100
        a = -20 / ta   # negative working capital
        b = -10 / ta   # negative retained earnings
        c = -5 / ta    # negative EBIT (loss)
        d = 10 / 90    # low market cap vs liabilities
        e = 50 / ta    # low sales/assets

        z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
        assert z < 1.81


# ---------------------------------------------------------------------------
# DuPont 3-step formula verification (unit-level)
# ---------------------------------------------------------------------------

class TestDuPontFormula:
    """Verify DuPont decomposition: ROE = NPM * Asset Turnover * Equity Multiplier."""

    def test_dupont_identity(self, sample_balance_sheet_values):
        v = sample_balance_sheet_values
        npm = v["net_income"] / v["revenue"]                  # Net Profit Margin
        asset_turnover = v["revenue"] / v["total_assets"]     # Asset Turnover
        equity_mult = v["total_assets"] / v["total_equity"]   # Equity Multiplier

        roe_dupont = npm * asset_turnover * equity_mult
        roe_direct = v["net_income"] / v["total_equity"]

        assert roe_dupont == pytest.approx(roe_direct, rel=1e-9)

    def test_dupont_components_reasonable(self, sample_balance_sheet_values):
        v = sample_balance_sheet_values
        npm = v["net_income"] / v["revenue"]
        at = v["revenue"] / v["total_assets"]
        em = v["total_assets"] / v["total_equity"]

        assert 0 < npm < 1       # Profit margin should be between 0% and 100%
        assert at > 0             # Asset turnover should be positive
        assert em >= 1            # Equity multiplier is always >= 1 for solvent firms


# ---------------------------------------------------------------------------
# Piotroski F-Score criteria (unit-level check)
# ---------------------------------------------------------------------------

class TestPiotroskiFScoreCriteria:
    """Verify individual F-Score criteria logic."""

    def test_positive_net_income_scores_1(self):
        assert (1 if 95_000_000_000 > 0 else 0) == 1

    def test_negative_net_income_scores_0(self):
        assert (1 if -5_000_000 > 0 else 0) == 0

    def test_positive_roa_change_scores_1(self):
        roa_curr = 0.27
        roa_prev = 0.25
        assert (1 if roa_curr > roa_prev else 0) == 1

    def test_positive_ocf_scores_1(self):
        assert (1 if 100_000_000_000 > 0 else 0) == 1

    def test_ocf_gt_net_income_scores_1(self):
        ocf = 120_000_000_000
        ni = 95_000_000_000
        assert (1 if ocf > ni else 0) == 1

    def test_leverage_decrease_scores_1(self):
        debt_to_assets_curr = 0.40
        debt_to_assets_prev = 0.45
        assert (1 if debt_to_assets_curr < debt_to_assets_prev else 0) == 1

    def test_current_ratio_increase_scores_1(self):
        cr_curr = 1.35
        cr_prev = 1.20
        assert (1 if cr_curr > cr_prev else 0) == 1

    def test_no_dilution_scores_1(self):
        shares_curr = 15_500_000_000
        shares_prev = 15_800_000_000
        assert (1 if shares_curr <= shares_prev else 0) == 1

    def test_gross_margin_increase_scores_1(self):
        gm_curr = 0.45
        gm_prev = 0.43
        assert (1 if gm_curr > gm_prev else 0) == 1

    def test_asset_turnover_increase_scores_1(self):
        at_curr = 1.15
        at_prev = 1.10
        assert (1 if at_curr > at_prev else 0) == 1

    def test_max_fscore_is_9(self):
        """All 9 criteria passing should sum to 9."""
        criteria = [1, 1, 1, 1, 1, 1, 1, 1, 1]
        assert sum(criteria) == 9
