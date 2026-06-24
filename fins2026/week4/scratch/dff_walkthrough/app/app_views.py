"""Streamlit layout and controls for the 50-stock portfolio app."""

from __future__ import annotations

import streamlit as st
from app.app_config import (
    ALL_TICKERS,
    APP_SUBTITLE,
    APP_TITLE,
    CONSTRAINT_LABELS,
    DEFAULT_VIEW,
    PORTFOLIO_LABELS,
    SECTOR_TICKERS,
    VIEW_OPTIONS,
)
from app.app_data import (
    asset_statistics,
    build_efficient_frontier,
    build_return_panel,
    compute_portfolio_returns,
    estimate_portfolios,
    load_equity_bundle,
    portfolio_scorecard,
)
from app.app_insights import (
    _compact_table_height,
    all_weights_table,
    efficient_frontier_figure,
    growth_figure,
    portfolio_weight_figure,
)

from fintools.apps import (
    active_tab_label,
    configure_page,
    lazy_tabs,
    query_choice,
    render_csv_download,
    render_data_health,
    render_display_table,
    sync_query_params,
    tab_is_open,
)


def _ticker_options() -> dict[str, str]:
    opts = {}
    for sector, tickers in SECTOR_TICKERS.items():
        for t in tickers:
            opts[t] = f"{t} ({sector})"
    return opts


def _initialize_state() -> None:
    default_tickers = ALL_TICKERS[:10]
    for ticker in ALL_TICKERS:
        key = f"dff_select_{ticker}"
        st.session_state.setdefault(key, ticker in default_tickers)


def _selected_tickers() -> list[str]:
    return [
        t for t in ALL_TICKERS
        if st.session_state.get(f"dff_select_{t}", False)
    ]


def render_sidebar() -> tuple[str, list[str]]:
    with st.sidebar:
        st.header("Controls")

        constraint_mode = st.radio(
            "Optimization mode",
            list(CONSTRAINT_LABELS),
            format_func=lambda k: CONSTRAINT_LABELS[k],
            key="dff_constraint",
        )

        st.subheader("Stock universe")
        st.caption("Select at least 2 stocks.")
        for sector, tickers in SECTOR_TICKERS.items():
            with st.expander(sector, expanded=True):
                for ticker in tickers:
                    st.checkbox(
                        f"{ticker}",
                        key=f"dff_select_{ticker}",
                    )

        selected = _selected_tickers()
        if len(selected) < 2:
            st.warning("Select at least 2 stocks.")

    return constraint_mode, selected


def main() -> None:
    _st = configure_page(APP_TITLE)
    _initialize_state()

    constraint_mode, selected_tickers = render_sidebar()

    _st.title(APP_TITLE)
    _st.caption(APP_SUBTITLE)

    price_panel = load_equity_bundle()
    _st.caption(
        f"Source: course equity bundle | "
        f"{price_panel['ticker'].nunique()} stocks, "
        f"{price_panel['date'].min():%Y-%m-%d} to {price_panel['date'].max():%Y-%m-%d}"
    )
    render_data_health(
        price_panel.loc[price_panel["ticker"].isin(selected_tickers or ALL_TICKERS[:1])],
        source="Course bundle",
        date_column="date",
        value_columns=["adjClose"],
    )

    if len(selected_tickers) < 2:
        _st.info("Select at least two stocks to build portfolios and view the efficient frontier.")
        return

    _wide, returns_wide = build_return_panel(price_panel, selected_tickers=selected_tickers)
    weights = estimate_portfolios(returns_wide, constraint_mode=constraint_mode)
    port_rets = compute_portfolio_returns(returns_wide, weights)
    metrics = portfolio_scorecard(port_rets)
    frontier = build_efficient_frontier(returns_wide, weights, constraint_mode=constraint_mode)
    astats = asset_statistics(returns_wide)

    view_default = query_choice("view", VIEW_OPTIONS, default=DEFAULT_VIEW)
    tabs = lazy_tabs(VIEW_OPTIONS, default=view_default, key="dff_view")
    active_view = active_tab_label(VIEW_OPTIONS, tabs, default=view_default)
    tab_weights, tab_growth, tab_frontier, tab_data = tabs

    if tab_is_open(tab_weights, fallback=active_view == "Portfolio Weights"):
        with tab_weights:
            st.subheader("Portfolio weights")
            st.markdown(
                f"**{len(selected_tickers)} stocks** selected. "
                f"Return panel: **{returns_wide.shape[0]} trading days** "
                f"({returns_wide.index.min():%Y-%m-%d} to {returns_wide.index.max():%Y-%m-%d})."
            )
            focus = st.radio(
                "Show weights for",
                list(PORTFOLIO_LABELS.values()),
                horizontal=True,
                key="dff_weight_focus",
            )
            key_map = {v: k for k, v in PORTFOLIO_LABELS.items()}
            st.plotly_chart(
                portfolio_weight_figure(weights, key_map[focus]),
                width="stretch",
            )
            wt = all_weights_table(weights)
            ht = _compact_table_height(wt, max_height=640)
            render_display_table(wt, reset_index=False, height=ht)
            render_csv_download(
                wt, label="Download weight table",
                file_name="dff_portfolio_weights.csv", key="dl_weights",
            )
            st.subheader("Scorecard")
            render_display_table(metrics, reset_index=False, height=_compact_table_height(metrics))
            render_csv_download(
                metrics, label="Download scorecard",
                file_name="dff_scorecard.csv", key="dl_scorecard",
            )

    if tab_is_open(tab_growth, fallback=active_view == "Growth of $1"):
        with tab_growth:
            st.subheader("Growth of $1")
            st.markdown(
                "How one dollar invested in each portfolio would have "
                "grown over the full sample."
            )
            st.plotly_chart(growth_figure(port_rets), width="stretch")
            render_display_table(metrics, reset_index=False, height=_compact_table_height(metrics))

    if tab_is_open(tab_frontier, fallback=active_view == "Efficient Frontier"):
        with tab_frontier:
            st.subheader("Efficient frontier")
            st.markdown(
                "The curve shows the best risk-return combinations available from the selected "
                "stocks. Each grey dot is one stock. The three portfolios are plotted as markers."
            )
            st.plotly_chart(
                efficient_frontier_figure(frontier, astats, metrics, weights),
                width="stretch",
            )

    if tab_is_open(tab_data, fallback=active_view == "Data"):
        with tab_data:
            st.subheader("Data and downloads")
            table_choice = st.segmented_control(
                "Show table",
                ["Returns", "Weights", "Scorecard"],
                key="dff_data_choice",
            ) or "Returns"
            if table_choice == "Returns":
                frame = returns_wide.copy().reset_index()
            elif table_choice == "Weights":
                frame = all_weights_table(weights)
            else:
                frame = metrics
            render_display_table(frame.tail(300), reset_index=False, height=460)
            render_csv_download(
                frame, label="Download displayed table",
                file_name=f"dff_{table_choice.lower()}.csv",
                key=f"dl_dff_{table_choice}",
            )

    sync_query_params(
        view=active_view,
        constraints=constraint_mode,
    )
