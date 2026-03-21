"""Pydantic request/response schemas for ATLAS Terminal API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TickerRequest(BaseModel):
    """Generic request carrying a ticker and optional market selector."""
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL, 005930.KS")
    market: str = Field(
        default="US (S&P/Dow/Nasdaq)",
        description="Market selector: US, South Korea (KOSPI/KOSDAQ), Japan (Nikkei), UK (LSE)",
    )


class EdgarRequest(BaseModel):
    """Request to download / fetch SEC EDGAR 10-K filings."""
    ticker: str = Field(..., description="Stock ticker symbol")
    email: str = Field(..., description="Email address required by SEC EDGAR fair-access policy")


class AnalysisRequest(BaseModel):
    """Request for AI-powered 10-K analysis (Gemini)."""
    ticker: str
    api_key: str = Field(..., description="Google Gemini API key")
    sector: str = ""
    industry: str = ""


class DCFInputs(BaseModel):
    """Inputs for discounted cash-flow valuation."""
    fcf: float = Field(..., description="Base free cash flow (trailing)")
    wacc: float = Field(..., description="Weighted-average cost of capital (decimal, e.g. 0.10)")
    terminal_growth: float = Field(..., description="Terminal growth rate (decimal, e.g. 0.025)")
    fcf_growth: float = Field(..., description="Near-term FCF growth rate (decimal, e.g. 0.12)")
    total_debt: float = Field(default=0, description="Total debt for bridge to equity value")
    cash: float = Field(default=0, description="Cash & equivalents for bridge to equity value")
    shares: float = Field(default=1, description="Shares outstanding for per-share value")


class CompanySearch(BaseModel):
    """Search for a company by name or partial ticker."""
    query: str = Field(..., description="Search term, e.g. 'Apple', 'Samsung'")
    market: str = ""


class CompsRequest(BaseModel):
    """Request for industry comparable companies data."""
    tickers: List[str] = Field(..., description="List of ticker symbols to compare")


class ForensicRequest(BaseModel):
    """Request for forensic audit analysis (Item 3 & 9A)."""
    ticker: str
    api_key: str
    item3: str = ""
    item9a: str = ""


class FinancialsLLMRequest(BaseModel):
    """Request to extract financials from Item 8 via LLM."""
    ticker: str
    api_key: str
    item8_text: str = ""


class PortfolioPositionCreate(BaseModel):
    """Create a new portfolio position."""
    ticker: str
    company_name: str = ""
    quantity: float
    avg_price: float
    currency: str = "USD"
    exchange: str = ""
    source: str = "manual"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class DCFResult(BaseModel):
    """Result of a DCF valuation calculation."""
    enterprise_value: float = 0
    equity_value: float = 0
    value_per_share: Optional[float] = None
    shares: Optional[float] = None
    scenarios: Dict[str, Any] = {}


class DCFInputsResponse(BaseModel):
    """Auto-filled DCF inputs from market data."""
    fcf: Optional[float] = None
    total_debt: float = 0
    cash: float = 0
    shares: Optional[float] = None


class SmartDefaultsResponse(BaseModel):
    """Smart defaults for DCF with analyst consensus guidance."""
    wacc: float = 0.10
    terminal_growth: float = 0.025
    fcf_growth: float = 0.10
    sector: str = "N/A"
    industry: str = "N/A"


class ConsensusResponse(BaseModel):
    """Analyst consensus data for a ticker."""
    target_mean: Optional[float] = None
    target_median: Optional[float] = None
    target_low: Optional[float] = None
    target_high: Optional[float] = None
    recommendation: str = ""
    num_analysts: int = 0
    data: Dict[str, Any] = {}


class SectorIndustryResponse(BaseModel):
    """Sector and industry classification."""
    sector: str = "N/A"
    industry: str = "N/A"


class FinancialHealth(BaseModel):
    """Comprehensive financial health metrics."""
    dupont: Dict[str, Any] = {}
    altman_z: Dict[str, Any] = {}
    red_flags: List[str] = []
    piotroski: Dict[str, Any] = {}


class PiotroskiResponse(BaseModel):
    """Piotroski F-Score breakdown."""
    score: int = 0
    criteria: List[Dict[str, Any]] = []
    used_ttm: bool = False


class SankeyData(BaseModel):
    """Income statement Sankey diagram data."""
    labels: List[str] = []
    sources: List[int] = []
    targets: List[int] = []
    values: List[float] = []
    colors: List[str] = []


class RadarMetrics(BaseModel):
    """Normalised radar chart metrics."""
    labels: List[str] = []
    values: List[float] = []
    raw: Dict[str, Any] = {}


class TrendData(BaseModel):
    """5-year financial trend data."""
    years: List[int] = []
    revenue: List[Optional[float]] = []
    net_income: List[Optional[float]] = []
    operating_margin: List[Optional[float]] = []
    fcf: List[Optional[float]] = []


class NewsItem(BaseModel):
    """A single news article."""
    title: str
    source: str = ""
    url: str = ""
    published_at: str = ""
    summary: str = ""


class PortfolioPosition(BaseModel):
    """A portfolio position with current market data."""
    id: Optional[str] = None
    ticker: str
    company_name: str = ""
    quantity: float
    avg_price: float
    currency: str = "USD"
    exchange: str = ""
    source: str = "manual"
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


class PortfolioSummary(BaseModel):
    """Aggregated portfolio summary."""
    total_value: float = 0
    total_cost: float = 0
    total_pnl: float = 0
    total_pnl_pct: Optional[float] = None
    positions: List[PortfolioPosition] = []


class MarketOverview(BaseModel):
    """Market overview with indices, FX, and crypto."""
    indices: Dict[str, Any] = {}
    fx_rates: Dict[str, float] = {}
    crypto: List[Dict[str, Any]] = []


class FXRateResponse(BaseModel):
    """Foreign exchange rate response."""
    pair: str
    rate: Optional[float] = None
    rates: Dict[str, float] = {}


class FXHistoryResponse(BaseModel):
    """FX pair historical data."""
    pair: str
    dates: List[str] = []
    rates: List[float] = []


class CryptoPrice(BaseModel):
    """Single cryptocurrency price data."""
    symbol: str
    name: str = ""
    price_usd: Optional[float] = None
    price_krw: Optional[float] = None
    change_24h_pct: Optional[float] = None


class EdgarSectionsResponse(BaseModel):
    """Cached or downloaded 10-K section texts."""
    status: str = ""
    item1a: str = ""
    item3: str = ""
    item7: str = ""
    item8: str = ""
    item9a: str = ""


class Item7Response(BaseModel):
    """Item 7 MD&A text."""
    item7: str = ""


class CompareResponse(BaseModel):
    """Comparison of latest vs 3-year-ago Item 7."""
    item1a_latest: str = ""
    item7_latest: str = ""
    item7_3y_ago: Optional[str] = None
    has_comparison: bool = False


class HealthCheckResponse(BaseModel):
    """API health check."""
    status: str = "ok"
    version: str = "1.0.0"
