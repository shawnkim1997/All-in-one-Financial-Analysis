/* eslint-disable @typescript-eslint/no-explicit-any */
import type { PeerData, RelativeValData, ValuationTier } from "../types";

/**
 * Pick the appropriate valuation framework given the company's profitability
 * profile. Mirrors the 4-tier policy described in the report design notes:
 *   1. DCF      — positive FCF
 *   2. EV/EBITDA — negative FCF but positive EBITDA (capex-heavy)
 *   3. P/S      — both negative but revenue is growing >10% YoY
 *   4. P/B (NAV) — fallback for asset-heavy or distressed names
 */
export function detectValuationTier(
  fcf: number | null,
  ebitda: number | null,
  revenueGrowth: number | null,
): ValuationTier {
  if (fcf != null && fcf > 0) return "dcf";
  if (ebitda != null && ebitda > 0) return "ev_ebitda";
  if (revenueGrowth != null && revenueGrowth > 0.10) return "ps_revenue";
  return "pb_nav";
}

interface DcfInputsLite {
  fcf: number;
  total_debt: number;
  cash: number;
  shares: number;
}

export function buildRelativeVal(
  tier: ValuationTier,
  peers: PeerData | null,
  info: Record<string, any>,
  di: DcfInputsLite | null,
  hi: any,
): RelativeValData | null {
  if (!di || !di.shares || di.shares <= 0) return null;
  const netDebt = (di.total_debt || 0) - (di.cash || 0);
  const revenue = hi?.revenue || info.totalRevenue || 0;
  const ebitda = hi?.ebitda || 0;
  const fcf = hi?.free_cash_flow ?? info.freeCashflow ?? di.fcf ?? 0;
  const revGrowth = hi?.revenue_growth ?? info.revenueGrowth ?? null;
  const profitMargin = hi?.profit_margin ?? info.profitMargins ?? 0;
  const rule40 = revGrowth != null ? revGrowth * 100 + profitMargin * 100 : null;
  const cash = di.cash || 0;
  const qBurn = fcf < 0 ? Math.abs(fcf) / 4 : 0;
  const cashRunway = qBurn > 0 ? cash / qBurn : null;

  if (tier === "ev_ebitda") {
    const peerAvg = peers?.averages?.ev_ebitda ?? 12;
    const impliedEV = peerAvg * ebitda;
    const baseVal = (impliedEV - netDebt) / di.shares;
    return {
      tier,
      tierLabel: "EV/EBITDA Relative Valuation",
      tierReason:
        "Free cash flow is negative due to heavy capital investment, but EBITDA is positive — the company generates operating profit before reinvestment.",
      method: "EV/EBITDA",
      multipleName: "EV/EBITDA",
      peerAvgMultiple: peerAvg,
      companyMetric: ebitda,
      metricLabel: "EBITDA",
      bear: { multiple: peerAvg * 0.7, value: (peerAvg * 0.7 * ebitda - netDebt) / di.shares },
      base: { multiple: peerAvg, value: baseVal },
      bull: { multiple: peerAvg * 1.3, value: (peerAvg * 1.3 * ebitda - netDebt) / di.shares },
      netDebt,
      shares: di.shares,
      cashRunwayQuarters: cashRunway,
      revenueGrowth: revGrowth,
      rule40,
      ebitda,
      fcf,
    };
  }
  if (tier === "ps_revenue") {
    const peerAvg = peers?.averages?.ps ?? 4;
    const impliedMC = peerAvg * revenue;
    const baseVal = impliedMC / di.shares;
    return {
      tier,
      tierLabel: "Price/Sales Relative Valuation",
      tierReason:
        "Both FCF and EBITDA are negative, but revenue is growing rapidly. P/S (Price-to-Sales) multiple is the appropriate valuation framework for high-growth, pre-profit companies.",
      method: "P/S",
      multipleName: "P/S",
      peerAvgMultiple: peerAvg,
      companyMetric: revenue,
      metricLabel: "Revenue",
      bear: { multiple: peerAvg * 0.6, value: (peerAvg * 0.6 * revenue) / di.shares },
      base: { multiple: peerAvg, value: baseVal },
      bull: { multiple: peerAvg * 1.5, value: (peerAvg * 1.5 * revenue) / di.shares },
      netDebt,
      shares: di.shares,
      cashRunwayQuarters: cashRunway,
      revenueGrowth: revGrowth,
      rule40,
      ebitda,
      fcf,
    };
  }
  // pb_nav
  const bookVal = hi?.book_value || 0;
  const peerAvg = peers?.averages?.pb ?? 2;
  const baseVal = bookVal > 0 ? bookVal * peerAvg : 0;
  return {
    tier,
    tierLabel: "Price/Book (NAV) Valuation",
    tierReason:
      "FCF, EBITDA, and revenue growth are all weak or negative. Asset-based valuation (P/B) provides the most relevant framework.",
    method: "P/B",
    multipleName: "P/B",
    peerAvgMultiple: peerAvg,
    companyMetric: bookVal * di.shares,
    metricLabel: "Book Value",
    bear: { multiple: peerAvg * 0.6, value: bookVal * peerAvg * 0.6 },
    base: { multiple: peerAvg, value: baseVal },
    bull: { multiple: peerAvg * 1.5, value: bookVal * peerAvg * 1.5 },
    netDebt,
    shares: di.shares,
    cashRunwayQuarters: cashRunway,
    revenueGrowth: revGrowth,
    rule40,
    ebitda,
    fcf,
  };
}
