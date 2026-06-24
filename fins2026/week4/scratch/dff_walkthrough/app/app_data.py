"""Cached data loading and portfolio math for the 50-stock app."""

from __future__ import annotations

import data_access
import numpy as np
import pandas as pd
import streamlit as st
from app.app_config import RISK_FREE
from dff_helpers import (
    TRADING_DAYS,
    annualized_stats,
    equal_weights,
    minimum_variance_weights,
    tangency_weights,
)
from dff_helpers import (
    efficient_frontier as closed_frontier,
)
from scipy.optimize import minimize


@st.cache_data(ttl=86400)
def load_equity_bundle() -> pd.DataFrame:
    return data_access.load_equity_prices()


def build_return_panel(
    price_panel: pd.DataFrame,
    *,
    selected_tickers: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    subset = price_panel.loc[price_panel["ticker"].isin(selected_tickers)].copy()
    wide = subset.pivot(index="date", columns="ticker", values="adjClose").sort_index()
    returns = wide.pct_change().dropna(how="all")
    return wide, returns


def _variance_objective(w: np.ndarray, cov: np.ndarray) -> float:
    return float(w @ cov @ w)


def _neg_sharpe_objective(
    w: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float
) -> float:
    excess = float(w @ mu - rf)
    vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
    if np.isclose(vol, 0.0):
        return 1e9
    return -(excess / vol)


def _solve_slsqp(
    objective, x0, args, bounds
) -> np.ndarray:
    result = minimize(
        objective,
        x0=x0,
        args=args,
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": 800, "ftol": 1e-12},
    )
    if not result.success:
        raise ValueError(f"Optimization failed: {result.message}")
    w = np.asarray(result.x, dtype=float)
    return w / float(w.sum())


def estimate_portfolios(
    returns_wide: pd.DataFrame,
    *,
    constraint_mode: str,
) -> pd.DataFrame:
    tickers = list(returns_wide.columns)
    n = len(tickers)
    arr = returns_wide.to_numpy(dtype=float)
    mu = arr.mean(axis=0)
    cov = np.cov(arr, rowvar=False, ddof=1)

    eq = equal_weights(n)

    if constraint_mode == "unconstrained":
        mv = minimum_variance_weights(cov)
        tan = tangency_weights(mu, cov, RISK_FREE)
    else:
        x0 = equal_weights(n)
        bounds = [(0.0, 1.0)] * n
        mv = _solve_slsqp(_variance_objective, x0, (cov,), bounds)
        tan = _solve_slsqp(_neg_sharpe_objective, x0, (mu, cov, RISK_FREE), bounds)

    frames = []
    for key, w in zip(["equal_weight", "minimum_variance", "mean_variance"], [eq, mv, tan]):
        frames.append(
            pd.DataFrame({"ticker": tickers, "portfolio": key, "weight": w})
        )
    return pd.concat(frames, ignore_index=True)


def compute_portfolio_returns(
    returns_wide: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    matrix = weights.pivot(index="ticker", columns="portfolio", values="weight")
    matrix = matrix.reindex(index=list(returns_wide.columns))
    arr = returns_wide.to_numpy(dtype=float) @ matrix.to_numpy(dtype=float)
    return pd.DataFrame(
        arr,
        index=returns_wide.index,
        columns=list(matrix.columns),
    )


def portfolio_scorecard(
    portfolio_returns: pd.DataFrame,
) -> pd.DataFrame:
    from app.app_config import PORTFOLIO_LABELS
    rows = []
    for col in portfolio_returns.columns:
        display = PORTFOLIO_LABELS.get(col, col)
        ann_ret, ann_vol, sharpe = annualized_stats(portfolio_returns[col].dropna(), RISK_FREE)
        wealth = (1.0 + portfolio_returns[col]).cumprod()
        dd = (wealth / wealth.cummax() - 1.0).min()
        rows.append({
            "Portfolio": display,
            "Ann. return (%)": round(ann_ret * 100, 1),
            "Ann. volatility (%)": round(ann_vol * 100, 1),
            "Sharpe ratio": round(sharpe, 2),
            "Max drawdown (%)": round(float(dd) * 100, 1),
        })
    return pd.DataFrame(rows)


def build_efficient_frontier(
    returns_wide: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    constraint_mode: str,
    n_points: int = 250,
) -> pd.DataFrame:
    tickers = list(returns_wide.columns)
    n = len(tickers)
    arr = returns_wide.to_numpy(dtype=float)
    mu = arr.mean(axis=0)
    cov = np.cov(arr, rowvar=False, ddof=1)

    if constraint_mode == "unconstrained":
        targets_d, vols_d = closed_frontier(mu, cov, n_points=n_points)
        return pd.DataFrame({
            "target_return_ann_pct": targets_d * TRADING_DAYS * 100,
            "volatility_ann_pct": vols_d * np.sqrt(TRADING_DAYS) * 100,
        })
    else:
        wm = weights.pivot(index="ticker", columns="portfolio", values="weight")
        wm = wm.reindex(index=tickers)
        eq_w = wm["equal_weight"].to_numpy(dtype=float)
        mv_w = wm["minimum_variance"].to_numpy(dtype=float)
        tan_w = wm["mean_variance"].to_numpy(dtype=float)

        eq_r = float(mu @ eq_w)
        mv_r = float(mu @ mv_w)
        tan_r = float(mu @ tan_w)
        upper = max(float(mu.max()), eq_r, tan_r)
        if np.isclose(upper, mv_r):
            upper = mv_r + 1e-4
        targets = np.linspace(mv_r, upper, n_points)

        rows = []
        guess = mv_w.copy()
        for target in targets:
            try:
                solved = _solve_slsqp(
                    _variance_objective,
                    guess,
                    (cov,),
                    [(0.0, 1.0)] * n,
                )
                _ = solved
                variance = float(solved @ cov @ solved)
                rows.append({
                    "target_return_ann_pct": target * TRADING_DAYS * 100,
                    "volatility_ann_pct": np.sqrt(max(variance, 0.0)) * np.sqrt(TRADING_DAYS) * 100,
                })
                guess = solved
            except ValueError:
                continue
        if not rows:
            raise ValueError("Efficient frontier produced no valid points.")
        result = pd.DataFrame(rows).drop_duplicates()
        return result.sort_values("volatility_ann_pct").reset_index(drop=True)


def asset_statistics(returns_wide: pd.DataFrame) -> pd.DataFrame:
    mu_d = returns_wide.mean()
    std_d = returns_wide.std(ddof=1)
    return pd.DataFrame({
        "ticker": returns_wide.columns,
        "annualized_return_pct": (mu_d * TRADING_DAYS * 100).values,
        "annualized_volatility_pct": (std_d * np.sqrt(TRADING_DAYS) * 100).values,
    }).sort_values("ticker").reset_index(drop=True)
