"""
All global constants, company lists, sector maps, regex patterns, row maps, and Damodaran baselines.
"""

# Company name → ticker for search/autocomplete (expand as needed)
COMPANY_LIST = [
    ("NVIDIA Corporation", "NVDA"), ("Apple Inc.", "AAPL"), ("Microsoft Corporation", "MSFT"),
    ("Amazon.com Inc.", "AMZN"), ("Alphabet Inc.", "GOOGL"), ("Meta Platforms Inc.", "META"),
    ("AMD", "AMD"), ("Intel Corporation", "INTC"), ("Qualcomm Inc.", "QCOM"), ("Tesla Inc.", "TSLA"),
    ("Berkshire Hathaway", "BRK.B"), ("JPMorgan Chase", "JPM"), ("Visa Inc.", "V"), ("UnitedHealth", "UNH"),
    ("Procter & Gamble", "PG"), ("Exxon Mobil", "XOM"), ("Johnson & Johnson", "JNJ"), ("Mastercard", "MA"),
    ("Chevron", "CVX"), ("Home Depot", "HD"), ("Merck", "MRK"), ("AbbVie", "ABBV"), ("Costco", "COST"),
    ("PepsiCo", "PEP"), ("Coca-Cola", "KO"), ("Pfizer", "PFE"), ("Walmart", "WMT"), ("Netflix", "NFLX"),
    ("Adobe", "ADBE"), ("Salesforce", "CRM"), ("Comcast", "CMCSA"), ("Cisco", "CSCO"), ("Oracle", "ORCL"),
    ("American Express", "AXP"), ("Bank of America", "BAC"), ("Wells Fargo", "WFC"), ("Verizon", "VZ"),
    ("AT&T", "T"), ("Walt Disney", "DIS"), ("Nike", "NKE"), ("McDonald's", "MCD"), ("Starbucks", "SBUX"),
    ("Goldman Sachs", "GS"), ("Morgan Stanley", "MS"), ("Target", "TGT"), ("Boeing", "BA"), ("IBM", "IBM"),
]
COMPANY_OPTIONS = [f"{t} - {n}" for n, t in COMPANY_LIST]
COMPANY_TICKER_MAP = {t: n for n, t in COMPANY_LIST}

MARKET_OPTIONS = [
    "US (S&P/Dow/Nasdaq)",
    "South Korea (KOSPI/KOSDAQ)",
    "Japan (Nikkei)",
    "UK (LSE)",
]

# Top-down sector analysis: industry → top 5 S&P 500 / NASDAQ tickers
SECTORS = {
    "Semiconductors & Hardware": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
    "Software & Cloud": ["MSFT", "ADBE", "CRM", "PANW", "CRWD"],
    "Consumer Retail": ["AMZN", "SBUX", "MCD", "WMT", "HD"],
    "Financial Services": ["JPM", "BAC", "GS", "MS", "V"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
}

# Section patterns for 10-K items
ITEM1A_PATTERNS = [
    r"Item\s+1A\s*[.:]\s*Risk\s+Factors",
    r"ITEM\s+1A\s*[.:]\s*Risk\s+Factors",
]
ITEM7_PATTERNS = [
    r"Item\s+7\s*[.:]\s*Management['\u2019]s\s+Discussion\s+and\s+Analysis",
    r"ITEM\s+7\s*[.:]\s*Management['\u2019]s\s+Discussion",
    r"Item\s+7\s*[.:]\s*[\w\s]+MD&A",
]
ITEM8_PATTERNS = [
    r"Item\s+8\s*[.:]\s*Financial\s+Statements",
    r"ITEM\s+8\s*[.:]\s*Financial\s+Statements",
]
ITEM3_PATTERNS = [
    r"Item\s+3\s*[.:]\s*Legal\s+Proceedings",
    r"ITEM\s+3\s*[.:]\s*Legal\s+Proceedings",
]
ITEM9A_PATTERNS = [
    r"Item\s+9A\s*[.:]\s*Controls\s+and\s+Procedures",
    r"Item\s+9A\s*[.:]\s*Internal\s+Control",
    r"ITEM\s+9A\s*[.:]\s*Controls",
]

# Gemini model config
GEMINI_MODEL = "gemini-2.0-flash"
RATE_LIMIT_WAIT_SEC = 60

# Financial statement required keys (for LLM extraction)
REQUIRED_FINANCIAL_KEYS = [
    "Revenue", "CostOfRevenue", "OperatingExpenses", "NetIncome",
    "TotalAssets", "CurrentAssets", "CurrentLiabilities", "LongTermDebt",
    "OperatingCashFlow", "SharesOutstanding",
]

# yahooquery: map to our index/column shape (index=line items, columns=dates)
INCOME_ROW_MAP = [
    ("Total Revenue", ("TotalRevenue", "OperatingRevenue", "TotalRevenue")),
    ("Cost Of Revenue", ("CostOfRevenue", "ReconciledCostOfRevenue")),
    ("Gross Profit", ("GrossProfit",)),
    ("Operating Income", ("OperatingIncome", "EBIT", "TotalOperatingIncomeAsReported")),
    ("Net Income", ("NetIncome", "NetIncomeCommonStockholders", "NetIncomeContinuousOperations", "DilutedNIAvailtoComStockholders")),
    ("Operating Expense", ("OperatingExpense", "OperatingExpenses", "TotalExpenses")),
    ("Interest Expense", ("InterestExpense", "InterestExpenseNonOperating")),
    ("Research And Development Expenses", ("ResearchAndDevelopment", "ResearchAndDevelopmentExpenses")),
]
BALANCE_ROW_MAP = [
    ("Total Assets", ("TotalAssets",)),
    ("Total Stockholder Equity", ("StockholdersEquity", "CommonStockEquity", "TotalEquityGrossMinorityInterest")),
    ("Total Liabilities", ("TotalLiabilitiesNetMinorityInterest", "TotalLiabilities")),
    ("Current Assets", ("CurrentAssets",)),
    ("Current Liabilities", ("CurrentLiabilities",)),
    ("Long Term Debt", ("LongTermDebt", "LongTermDebtAndCapitalLeaseObligation")),
    ("Total Debt", ("TotalDebt",)),
    ("Share Issued", ("OrdinarySharesNumber", "ShareIssued", "BasicAverageShares", "DilutedAverageShares")),
    ("Cash And Cash Equivalents", ("CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments", "EndCashPosition")),
    ("Retained Earnings", ("RetainedEarnings",)),
]
CASHFLOW_ROW_MAP = [
    ("Operating Cash Flow", ("OperatingCashFlow", "CashFromOperatingActivities")),
    ("Capital Expenditure", ("CapitalExpenditure", "CapitalExpenditures")),
]

# Aswath Damodaran sector WACC (approx. 2024/2025 baseline). Used for reference in DCF panel.
DAMODARAN_WACC = {
    "Software": 8.5,
    "Retail": 7.5,
    "Hardware": 9.0,
    "Financials": 8.0,
    "Healthcare": 7.2,
    "Consumer": 7.5,
    "Technology": 8.5,
    "Industrial": 7.8,
    "Energy": 8.2,
    "Utilities": 6.5,
}
DAMODARAN_ERP_PCT = 4.6
DAMODARAN_RF_PCT = 4.2
