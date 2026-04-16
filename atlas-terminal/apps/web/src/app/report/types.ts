/**
 * Type definitions for the institutional report data flow.
 *
 * Many of the upstream API responses are still untyped on the backend
 * (`Dict[str, Any]`), so a number of fields keep loose `Record<string, unknown>`
 * shapes. P1-4 / P2-1 will tighten these as Pydantic response models land.
 */

export type FinancialPeriod = Record<string, unknown>;

export interface ResearchDash {
  ticker: string;
  fscore_total: number;
  fscore_criteria: { key: string; label: string; history: { year: number; pass_flag: boolean }[] }[];
  dupont_tree?: {
    root: { value: number };
    npm: { value: number; trend: string };
    asset_turnover: { value: number; trend: string };
    equity_mult: { value: number; trend: string };
  };
  sankey: unknown;
  waterfall: { id: string; label: string; value: number; cumulative: number; step_type: string }[];
  anomalies: { account_key: string; display_name: string; change_pct: number; direction: string }[];
  error?: string;
}

export interface InstitutionalData {
  ticker: string;
  sections: Record<string, string>;
  quant_context: string;
}

export interface DCFResult {
  base: number | null;
  bull: number | null;
  bear: number | null;
  current_price: number | null;
  scenarios: Record<string, { intrinsic_value: number | null; upside: number }>;
}

export interface SensitivityResult {
  wacc_values: number[];
  tg_values: number[];
  matrix: (number | null)[][];
}

export interface MonteCarloResult {
  histogram: { counts: number[]; bin_edges: number[] };
  mean: number | null;
  median: number | null;
  percentile_5: number | null;
  percentile_95: number | null;
  upside_pct: number | null;
  current_price: number | null;
}

export interface TornadoItem {
  variable: string;
  low: number;
  high: number;
  base: number;
}

export interface ReverseDCFResult {
  implied_growth: number | null;
  current_price: number | null;
}

export interface ConsensusData {
  target_mean: number | null;
  target_high: number | null;
  target_low: number | null;
  target_median: number | null;
  recommendation: string;
  num_analysts: number;
}

export interface PeerData {
  ticker: string;
  sector: string;
  industry: string;
  averages: Record<string, number | null>;
  peers: Record<string, unknown>[];
}

export interface EarningsHistory {
  date: string;
  eps_actual: number | null;
  eps_estimate: number | null;
  surprise: number;
}

export interface QuarterlyEarnings {
  period: string;
  revenue: number | null;
  earnings: number | null;
}

export interface HealthData {
  dupont: Record<string, number>;
  altman_z: number | null;
  current_ratio: number | null;
  interest_coverage: number | null;
  debt_to_equity: number | null;
  red_flags: string[];
}

export type TechnicalData = Record<string, unknown>;

export type ValuationTier = "dcf" | "ev_ebitda" | "ps_revenue" | "pb_nav";

export interface RelativeValData {
  tier: ValuationTier;
  tierLabel: string;
  tierReason: string;
  method: string;
  multipleName: string;
  peerAvgMultiple: number;
  companyMetric: number;
  metricLabel: string;
  bear: { multiple: number; value: number };
  base: { multiple: number; value: number };
  bull: { multiple: number; value: number };
  netDebt: number;
  shares: number;
  cashRunwayQuarters: number | null;
  revenueGrowth: number | null;
  rule40: number | null;
  ebitda: number | null;
  fcf: number | null;
}

export type InfoMap = Record<string, unknown>;

export interface StatementsBundle {
  income_statement?: FinancialPeriod[];
  balance_sheet?: FinancialPeriod[];
  cash_flow?: FinancialPeriod[];
}
