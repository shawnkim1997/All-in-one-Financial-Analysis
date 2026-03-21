"""Monte Carlo simulation for DCF valuation.

Runs N random DCF scenarios by sampling WACC and FCF growth from
normal distributions, then reports distributional statistics.
"""

from typing import Dict, Any, List

import numpy as np


def run_monte_carlo_dcf(
    fcf: float,
    wacc_mean: float,
    wacc_std: float,
    growth_mean: float,
    growth_std: float,
    term_growth: float,
    total_debt: float,
    cash: float,
    shares: float,
    n_simulations: int = 5000,
    current_price: float | None = None,
) -> Dict[str, Any]:
    """Run a Monte Carlo DCF simulation.

    Parameters
    ----------
    fcf : float
        Base free cash flow.
    wacc_mean / wacc_std : float
        Mean and standard deviation for WACC sampling (decimal, e.g. 0.09).
    growth_mean / growth_std : float
        Mean and standard deviation for FCF growth sampling (decimal).
    term_growth : float
        Terminal growth rate (constant across simulations).
    total_debt, cash, shares : float
        Balance-sheet items for equity bridge.
    n_simulations : int
        Number of Monte Carlo iterations (default 5 000).
    current_price : float | None
        Current market price; used to compute prob_above_current.

    Returns
    -------
    dict
        values          – list of per-share intrinsic values (sorted)
        percentile_10   – 10th percentile
        median          – 50th percentile
        percentile_90   – 90th percentile
        mean            – arithmetic mean
        prob_above_current – probability the simulated value exceeds current_price
        current_price   – echo back
        n_simulations   – echo back
    """
    if shares <= 0 or fcf <= 0:
        return {
            "values": [],
            "percentile_10": None,
            "median": None,
            "percentile_90": None,
            "mean": None,
            "prob_above_current": None,
            "current_price": current_price,
            "n_simulations": n_simulations,
        }

    rng = np.random.default_rng()

    # Sample WACC and growth; clip to sensible bounds
    waccs = rng.normal(wacc_mean, max(wacc_std, 1e-6), n_simulations)
    waccs = np.clip(waccs, 0.01, 0.40)

    growths = rng.normal(growth_mean, max(growth_std, 1e-6), n_simulations)
    growths = np.clip(growths, -0.30, 0.60)

    projection_years = 10
    values: List[float] = []

    for w, g in zip(waccs, growths):
        if w <= term_growth:
            continue
        # 10-year two-stage DCF (simplified: constant growth then terminal)
        pv = 0.0
        fcft = float(fcf)
        for t in range(1, projection_years + 1):
            fcft *= (1 + g)
            pv += fcft / ((1 + w) ** t)
        tv = fcft * (1 + term_growth) / (w - term_growth)
        pv += tv / ((1 + w) ** projection_years)
        equity = pv - total_debt + cash
        per_share = equity / shares
        if per_share > 0:
            values.append(round(per_share, 2))

    if not values:
        return {
            "values": [],
            "percentile_10": None,
            "median": None,
            "percentile_90": None,
            "mean": None,
            "prob_above_current": None,
            "current_price": current_price,
            "n_simulations": n_simulations,
        }

    arr = np.array(values)
    arr.sort()

    prob_above = None
    if current_price is not None and current_price > 0:
        prob_above = round(float(np.mean(arr > current_price) * 100), 1)

    return {
        "values": arr.tolist(),
        "percentile_10": round(float(np.percentile(arr, 10)), 2),
        "median": round(float(np.median(arr)), 2),
        "percentile_90": round(float(np.percentile(arr, 90)), 2),
        "mean": round(float(np.mean(arr)), 2),
        "prob_above_current": prob_above,
        "current_price": current_price,
        "n_simulations": n_simulations,
    }
