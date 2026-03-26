export interface FScoreYearPoint {
  year: number;
  pass_flag: boolean;
}

export interface FScoreCriterionSeries {
  key: string;
  label: string;
  history: FScoreYearPoint[];
}

export interface DuPontTreeNode {
  id: string;
  label: string;
  value: number;
  unit: string;
  avg_5y?: number | null;
  vs_5y_avg_pct?: number | null;
  trend: string;
}

export interface DuPontTreePayload {
  root: DuPontTreeNode;
  npm: DuPontTreeNode;
  asset_turnover: DuPontTreeNode;
  equity_mult: DuPontTreeNode;
}

export interface SankeyNivoNode {
  id: string;
  label?: string | null;
}

export interface SankeyNivoLink {
  source: string;
  target: string;
  value: number;
}

export interface WaterfallStep {
  id: string;
  label: string;
  value: number;
  cumulative: number;
  step_type: string;
}

export interface FinancialAnomalyItem {
  account_key: string;
  display_name: string;
  prior_value?: number | null;
  current_value?: number | null;
  change_pct?: number | null;
  direction: string;
}

export interface ResearchDashboardPayload {
  ticker: string;
  fscore_total: number;
  fscore_criteria: FScoreCriterionSeries[];
  dupont_tree: DuPontTreePayload | null;
  sankey: {
    nodes: SankeyNivoNode[];
    links: SankeyNivoLink[];
  };
  waterfall: WaterfallStep[];
  anomalies: FinancialAnomalyItem[];
  error?: string | null;
}

export interface AnomalyExplainResult {
  summary: string;
  likely_causes: string[];
  citations: { excerpt: string; context: string }[];
  confidence: string;
}
