"""Portfolio risk metrics -- VaR, Sharpe, Sortino, MDD, Beta, Correlation."""

import numpy as np


def compute_portfolio_risk(positions: list, benchmark: str = "SPY") -> dict:
    """Compute VaR, Sharpe, Sortino, MDD, Beta, Correlation for portfolio."""
    import yfinance as yf

    tickers = [p["ticker"] for p in positions]
    if not tickers:
        return {}

    values = [
        p.get("value", p.get("quantity", 0) * p.get("avg_price", 0))
        for p in positions
    ]
    total = sum(values) or 1
    weights = np.array([v / total for v in values])

    data = yf.download(tickers + [benchmark], period="1y", progress=False)["Close"]
    if data.empty:
        return {}

    returns = data.pct_change().dropna()

    if len(tickers) == 1:
        port_returns = (
            returns[tickers[0]]
            if tickers[0] in returns.columns
            else returns.iloc[:, 0]
        )
    else:
        ticker_returns = (
            returns[tickers]
            if all(t in returns.columns for t in tickers)
            else returns.iloc[:, : len(tickers)]
        )
        port_returns = (ticker_returns * weights).sum(axis=1)

    bench_returns = (
        returns[benchmark] if benchmark in returns.columns else returns.iloc[:, -1]
    )

    # VaR
    var_95 = float(np.percentile(port_returns, 5))
    var_99 = float(np.percentile(port_returns, 1))

    # Sharpe (annualized, rf=0.04)
    rf_daily = 0.04 / 252
    excess = port_returns - rf_daily
    sharpe = (
        float(np.sqrt(252) * excess.mean() / excess.std())
        if excess.std() > 0
        else 0
    )

    # Sortino
    downside = excess[excess < 0]
    sortino = (
        float(np.sqrt(252) * excess.mean() / downside.std())
        if len(downside) > 0 and downside.std() > 0
        else 0
    )

    # Max Drawdown
    cumulative = (1 + port_returns).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (cumulative - peak) / peak
    max_dd = float(drawdown.min())

    # Beta
    cov = np.cov(port_returns, bench_returns)
    beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0

    # Correlation matrix
    corr = {}
    if len(tickers) > 1:
        corr_df = (
            returns[tickers].corr()
            if all(t in returns.columns for t in tickers)
            else {}
        )
        if hasattr(corr_df, "to_dict"):
            corr = {
                str(k): {str(k2): round(v2, 3) for k2, v2 in v.items()}
                for k, v in corr_df.to_dict().items()
            }

    return {
        "var_95": round(var_95 * 100, 2),
        "var_99": round(var_99 * 100, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "beta": round(beta, 2),
        "correlation_matrix": corr,
    }
