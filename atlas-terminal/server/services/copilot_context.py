"""Build compact copilot context with asset-type aware fields."""

from __future__ import annotations


def build_copilot_context(asset_type: str, data: dict) -> str:
    parts: list[str] = []
    if asset_type == "etf":
        parts.append(f"[Asset Type] ETF — {data.get('category')}")
        parts.append(f"[ETF] AUM: {data.get('aum')}, Expense: {data.get('expense_ratio')}")
        r = data.get("returns") or {}
        parts.append(f"[Performance] YTD: {r.get('ytd')}%, 1Y: {r.get('1y')}%")
    elif asset_type == "commodity_future":
        parts.append(f"[Asset Type] Commodity Future — {data.get('name')}")
        parts.append(f"[Commodity] Open Interest: {data.get('open_interest')}")
        seasonal = data.get("seasonal_pattern") or {}
        if seasonal:
            best_month = max(seasonal, key=lambda k: seasonal[k])
            worst_month = min(seasonal, key=lambda k: seasonal[k])
            parts.append(f"[Seasonal] Best month: {best_month}, Worst: {worst_month}")
    else:
        parts.append("[Asset Type] Equity")
        parts.append(f"[Sector] {data.get('sector')}")
    return "\n".join(parts)
