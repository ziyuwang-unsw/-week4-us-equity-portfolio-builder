"""Configuration constants for the 50-stock portfolio app."""

from __future__ import annotations

SECTOR_TICKERS = {
    "Comm": ["CMCSA", "EA", "T", "TMUS", "TTWO"],
    "Consumer": ["DIS", "KO", "NKE", "SBUX", "WMT"],
    "Energy": ["COP", "CVX", "OXY", "SLB", "XOM"],
    "Financials": ["GS", "MS", "USB", "V", "WFC"],
    "Healthcare": ["ABBV", "ABT", "AMGN", "GILD", "MRK"],
    "Industrials": ["BA", "CAT", "GE", "MMM", "UPS"],
    "Materials": ["DD", "DOW", "NEM", "NUE", "SHW"],
    "RealEstate": ["AMT", "CCI", "O", "PLD", "PSA"],
    "Tech": ["ADBE", "AMD", "INTC", "NVDA", "QCOM"],
    "Utilities": ["AEP", "D", "DUK", "NEE", "SO"],
}

ALL_TICKERS = sorted(t for group in SECTOR_TICKERS.values() for t in group)

TICKER_SECTOR = {t: s for s, ts in SECTOR_TICKERS.items() for t in ts}

APP_TITLE = "50-Stock Portfolio Builder"
APP_SUBTITLE = (
    "Explore the full 50-stock course universe. Pick any subset, compare "
    "equal-weight, minimum-variance, and mean-variance portfolios, and "
    "inspect the efficient frontier — all in-sample."
)

PORTFOLIO_LABELS = {
    "equal_weight": "Equal-weight",
    "minimum_variance": "Minimum-variance",
    "mean_variance": "Mean-variance (tangency)",
}
PORTFOLIO_KEYS = list(PORTFOLIO_LABELS)

PORTFOLIO_COLORS = {
    "Equal-weight": "#6F6A61",
    "Minimum-variance": "#2F7F73",
    "Mean-variance (tangency)": "#990F3D",
}

CONSTRAINT_LABELS = {
    "unconstrained": "Unconstrained (short sales allowed)",
    "long_only": "Long-only",
}

VIEW_OPTIONS = [
    "Portfolio Weights",
    "Growth of $1",
    "Efficient Frontier",
    "Data",
]
DEFAULT_VIEW = "Portfolio Weights"
DEFAULT_CONSTRAINT = "unconstrained"
RISK_FREE = 0.0
