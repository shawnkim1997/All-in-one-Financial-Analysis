"""
Plotly chart builders: Sankey, Radar, dark theme.
"""
try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def _build_sankey_figure(data: dict) -> "go.Figure":
    """Sankey: Revenue -> COGS + Gross Profit; Gross Profit -> OpEx + OpInc; OpInc -> Tax/Interest/Other + Net Income."""
    if go is None:
        return None
    rev, cogs, gp, opex, opinc, tax_other, ni = (
        data["revenue"], data["cogs"], data["gross_profit"], data["opex"],
        data["operating_income"], data["tax_interest_other"], data["net_income"],
    )
    if rev <= 0:
        return None
    # Format labels with dollar values
    def _fmt(label, val):
        if abs(val) >= 1e9:
            return f"{label}<br>${val/1e9:.1f}B"
        if abs(val) >= 1e6:
            return f"{label}<br>${val/1e6:.0f}M"
        return label
    nodes = [
        _fmt("Revenue", rev), _fmt("Cost of Revenue", cogs), _fmt("Gross Profit", gp),
        _fmt("Operating Exp.", opex), _fmt("Operating Inc.", opinc),
        _fmt("Tax/Int./Other", tax_other), _fmt("Net Income", ni),
    ]
    node_colors = [
        "#3B82F6",   # Revenue — blue
        "#F87171",   # COGS — red
        "#34D399",   # Gross Profit — green
        "#FB923C",   # OpEx — orange
        "#60A5FA",   # Operating Income — light blue
        "#9CA3AF",   # Tax/Interest — grey
        "#10B981",   # Net Income — bright green
    ]
    link_colors = [
        "rgba(248,113,113,0.3)",  # Rev -> COGS (red flow)
        "rgba(52,211,153,0.3)",   # Rev -> GP (green flow)
        "rgba(251,146,60,0.3)",   # GP -> OpEx (orange flow)
        "rgba(96,165,250,0.3)",   # GP -> OpInc (blue flow)
        "rgba(156,163,175,0.25)", # OpInc -> Tax (grey flow)
        "rgba(16,185,129,0.35)",  # OpInc -> NI (green flow)
    ]
    source = [0, 0, 2, 2, 4, 4]
    target = [1, 2, 3, 4, 5, 6]
    value = [max(0, float(v)) for v in [cogs, gp, opex, opinc, tax_other, ni]]
    fig = go.Figure(data=[go.Sankey(
        node=dict(label=nodes, color=node_colors, pad=20, thickness=24,
                  line=dict(color="rgba(255,255,255,0.1)", width=1)),
        link=dict(source=source, target=target, value=value, color=link_colors),
    )])
    fig.update_layout(
        title=dict(text="Income Statement Flow", font=dict(size=14, color="#F3F4F6", family="Inter")),
        height=420, margin=dict(t=45, b=15, l=10, r=10),
        font=dict(size=12, color="#D1D5DB", family="Inter"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _build_radar_common(theta_list, r_list, title_text="Financial Health Radar") -> "go.Figure":
    """Shared radar chart builder with Soft Navy theme."""
    if go is None:
        return None
    theta = theta_list + [theta_list[0]]
    r = r_list + [r_list[0]]
    fig = go.Figure()
    # Add a "benchmark 50" ring for reference
    fig.add_trace(go.Scatterpolar(
        r=[50] * (len(theta_list) + 1), theta=theta,
        fill="toself", fillcolor="rgba(255,255,255,0.02)",
        line=dict(color="rgba(255,255,255,0.1)", width=1, dash="dot"),
        name="Avg (50)", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatterpolar(
        r=r, theta=theta, fill="toself",
        fillcolor="rgba(59, 130, 246, 0.2)",
        line=dict(color="#60A5FA", width=2.5),
        marker=dict(size=6, color="#60A5FA", symbol="circle"),
        name="Score",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], tickvals=[20, 40, 60, 80],
                            tickfont=dict(size=9, color="#4B5563", family="JetBrains Mono"),
                            gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.06)"),
            angularaxis=dict(tickfont=dict(size=11, color="#D1D5DB", family="Inter"),
                             gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.08)"),
        ),
        title=dict(text=title_text, font=dict(size=14, color="#F3F4F6", family="Inter")),
        height=420, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=45, b=25, l=60, r=60),
    )
    return fig


def _build_radar_figure_from_metrics(metrics: dict) -> "go.Figure":
    """Build radar chart from precomputed metrics dict."""
    if not metrics or not metrics.get("r"):
        return None
    return _build_radar_common(metrics["theta"], metrics["r"], "Financial Health Radar (10-K Item 8)")


def _radar_norm(roe_pct, current_ratio, asset_turnover, equity_mult, rev_yoy_pct):
    """Normalize 5 raw metrics to 0-100 for radar (same logic as get_radar_metrics_normalized)."""
    def n_roe(x): return min(100, max(0, (x + 10) / 40 * 100)) if x is not None else 50
    def n_cr(x): return min(100, max(0, x / 3 * 100)) if x is not None else 50
    def n_at(x): return min(100, max(0, x * 50)) if x is not None else 50
    def n_em(x): return min(100, max(0, (x - 0.5) / 2.5 * 100)) if x is not None else 50
    def n_yoy(x): return min(100, max(0, (x + 20) / 50 * 100)) if x is not None else 50
    return [n_roe(roe_pct), n_cr(current_ratio), n_at(asset_turnover), n_em(equity_mult), n_yoy(rev_yoy_pct)]


def _build_radar_from_manual(roe_pct, current_ratio, asset_turnover, equity_mult, rev_yoy_pct) -> "go.Figure":
    """Build radar chart from 5 manually entered ratios (fallback)."""
    theta = ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"]
    r = _radar_norm(roe_pct, current_ratio, asset_turnover, equity_mult, rev_yoy_pct)
    return _build_radar_common(theta, r, "Financial Health Radar (Manual)")


def _apply_dark_theme(fig):
    """Apply Soft Navy theme to Plotly figures."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        font=dict(color='#D1D5DB', family='Inter, JetBrains Mono, sans-serif', size=12),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)', tickfont=dict(family='JetBrains Mono', size=11)),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)', tickfont=dict(family='JetBrains Mono', size=11)),
        legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.06)', font=dict(size=11)),
        title_font=dict(color='#F3F4F6', size=14),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig
