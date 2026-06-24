"""Plotly figures and formatting helpers for the 50-stock app."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from app.app_config import PORTFOLIO_COLORS, PORTFOLIO_LABELS

from fintools.apps import apply_app_plotly_theme


def _compact_table_height(
    frame: pd.DataFrame,
    row_height: int = 35,
    header_height: int = 38,
    min_height: int = 118,
    max_height: int = 520,
) -> int:
    if frame.empty:
        return min_height
    return min(max_height, max(min_height, header_height + row_height * len(frame)))


def format_signed(value: float, decimals: int = 1) -> str:
    return f"{value:+,.{decimals}f}%"


def portfolio_weight_figure(weights: pd.DataFrame, portfolio_key: str) -> go.Figure:
    label = PORTFOLIO_LABELS[portfolio_key]
    frame = (
        weights.loc[weights["portfolio"] == portfolio_key, ["ticker", "weight"]]
        .copy()
        .sort_values("weight")
        .reset_index(drop=True)
    )
    n = len(frame)
    color = PORTFOLIO_COLORS[label]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=frame["weight"] * 100,
            y=frame["ticker"],
            orientation="h",
            marker_color=color,
            hovertemplate="%{y}<br>Weight: %{x:.2f}%<extra></extra>",
            showlegend=False,
        )
    )
    fig.add_vline(x=0, line_color="#9AA3AD", line_dash="dot")
    fig.update_layout(title={"text": f"{label} weights", "x": 0, "xanchor": "left"})
    apply_app_plotly_theme(
        fig,
        yaxis_title=None,
        height=max(300, n * 14),
        range_selector=False,
        range_slider=False,
    )
    fig.update_xaxes(title="Weight (%)", showgrid=True)
    fig.update_yaxes(title=None, automargin=True)
    return fig


def all_weights_table(weights: pd.DataFrame) -> pd.DataFrame:
    matrix = (
        weights.pivot(index="ticker", columns="portfolio", values="weight")
        .mul(100)
        .round(1)
        .reset_index()
        .rename(columns={"ticker": "Ticker"})
    )
    matrix = matrix.rename(
        columns={
            k: PORTFOLIO_LABELS[k]
            for k in PORTFOLIO_LABELS
        }
    )
    total = pd.DataFrame({"Ticker": ["Total"], **{
        PORTFOLIO_LABELS[k]: [matrix[PORTFOLIO_LABELS[k]].sum()]
        for k in PORTFOLIO_LABELS
    }})
    return pd.concat([matrix, total], ignore_index=True)


def growth_figure(portfolio_returns: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    wealth_series = []
    for col in portfolio_returns.columns:
        display = PORTFOLIO_LABELS.get(col, col)
        wealth = (1.0 + portfolio_returns[col].astype(float)).cumprod()
        wealth_series.append(wealth)
        fig.add_trace(
            go.Scatter(
                x=portfolio_returns.index,
                y=wealth,
                mode="lines",
                name=display,
                line={"width": 2.2, "color": PORTFOLIO_COLORS.get(display, "#6F6A61")},
                hovertemplate="%{x|%Y-%m-%d}<br>Growth of $1: %{y:.2f}<extra></extra>",
            )
        )
    fig.update_layout(title={"text": "Growth of $1", "x": 0, "xanchor": "left"})
    apply_app_plotly_theme(fig, yaxis_title="Growth of $1", height=520, range_slider=False)
    combined = pd.concat(wealth_series, ignore_index=True)
    pos = combined.loc[combined > 0]
    if not pos.empty:
        import math
        lo = float(pos.min()) / 1.05
        hi = float(pos.max()) * 1.05
        start_exp = math.floor(math.log10(lo)) - 1
        end_exp = math.ceil(math.log10(hi)) + 1
        tickvals = sorted(set(
            m * 10 ** e
            for e in range(start_exp, end_exp + 1)
            for m in (1.0, 2.0, 5.0)
            if lo <= m * 10 ** e <= hi
        ))
        if tickvals:
            ticktext = [
                f"${v:,.0f}" if v >= 10
                else f"${v:,.1f}".rstrip("0").rstrip(".")
                for v in tickvals
            ]
            fig.update_yaxes(
                type="log",
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
                title="Growth of $1 (log scale)",
                automargin=True,
            )
    fig.add_hline(y=1.0, line_color="#9AA3AD", line_dash="dot")
    return fig


def efficient_frontier_figure(
    frontier: pd.DataFrame,
    asset_stats: pd.DataFrame,
    metrics: pd.DataFrame,
    weights: pd.DataFrame,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=asset_stats["annualized_volatility_pct"],
            y=asset_stats["annualized_return_pct"],
            mode="markers+text",
            text=asset_stats["ticker"],
            textposition="top center",
            marker={
                "size": 10, "color": "rgba(120,120,120,0.35)",
                "line": {"color": "rgba(120,120,120,0.65)", "width": 1},
            },
            name="Individual stocks",
            hovertemplate="%{text}<br>Ann. vol: %{x:.1f}%<br>Ann. return: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frontier["volatility_ann_pct"],
            y=frontier["target_return_ann_pct"],
            mode="lines",
            name="Efficient frontier",
            line={"color": "#2F455C", "width": 3},
            hovertemplate="Ann. vol: %{x:.1f}%<br>Ann. return: %{y:.1f}%<extra></extra>",
        )
    )
    markers = {"equal_weight": "square", "minimum_variance": "diamond", "mean_variance": "circle"}
    for key, label in PORTFOLIO_LABELS.items():
        matched = metrics.loc[metrics["Portfolio"] == label]
        if matched.empty:
            continue
        row = matched.iloc[0]
        vol = float(row["Ann. volatility (%)"])
        ret = float(row["Ann. return (%)"])
        fig.add_trace(
            go.Scatter(
                x=[vol],
                y=[ret],
                mode="markers",
                marker={
                    "size": 16, "symbol": markers.get(key, "circle"),
                    "color": PORTFOLIO_COLORS[label],
                },
                name=label,
                hovertemplate=(
                    f"{label}<br>Ann. vol: %{{x:.1f}}%<br>"
                    f"Ann. return: %{{y:.1f}}%<extra></extra>"
                ),
            )
        )
        fig.add_annotation(
            x=vol, y=ret, ax=20, ay=-20 if key != "minimum_variance" else 20,
            text=label, showarrow=True, arrowhead=0, arrowsize=1,
            bgcolor="rgba(255,255,255,0.92)", bordercolor=PORTFOLIO_COLORS[label], borderwidth=1,
        )
    fig.update_layout(
        title={"text": "Efficient frontier", "x": 0, "xanchor": "left"},
        height=560,
        hovermode="closest",
    )
    apply_app_plotly_theme(
        fig, yaxis_title="Annualized return (%)",
        range_selector=False, range_slider=False,
    )
    fig.update_xaxes(title="Annualized volatility (%)", showgrid=True)
    return fig
