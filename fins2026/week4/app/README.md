# Week 4 U.S. Equity Portfolio App

This is the client-facing Week 4 product surface. It narrows the lecture code
to a 10-stock U.S. equity universe and lets a user compare:

- a custom allocation
- an equal-weight benchmark
- a minimum-variance portfolio
- a mean-variance portfolio

The app is **in-sample only**. It compares historical portfolio behavior over
the selected window, but it does not yet implement rolling or out-of-sample
portfolio re-estimation.

## Run locally

Run from the repo root:

```bash
streamlit run fins2026/week4/app/streamlit_app.py
```

The app first tries live Yahoo Finance prices and live Kenneth French daily
risk-free data. If a live refresh fails, it falls back to the committed fixture
bundle in `app/fixtures/`.

## App fixture

Refresh the committed fallback fixture with:

```bash
python fins2026/week4/scripts/build_week4_app_fixture.py
```

The app fixture currently includes:

- `fixtures/yahoo_app_10_long.parquet`
- `fixtures/french_daily_rfr.parquet`

## App structure

- `app_config.py`: labels, options, and display constants
- `app_data.py`: live/fallback data loading and sample filtering
- `app_insights.py`: Plotly figures, metric cards, and formatting helpers
- `app_views.py`: Streamlit layout, controls, tabs, and downloads
- `streamlit_app.py`: repo bootstrap and `main()` entrypoint

## Deployment

Before deployment, run from the repo root:

```bash
python tools/workflow.py check-app-submission --target fins2026/week4 --entrypoint fins2026/week4/app/streamlit_app.py
```

To prepare a clean private deploy repo, run:

```bash
python tools/workflow.py prepare-app-repo --source fins2026/week4 --dest ../week4-us-equity-portfolio-builder --repo week4-us-equity-portfolio-builder --entrypoint fins2026/week4/app/streamlit_app.py
```
