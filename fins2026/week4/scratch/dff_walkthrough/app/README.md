# 50-Stock Portfolio Builder

Streamlit app for the Data Factory Floor walkthrough (Week 4). Loads the
50-stock course equity dataset and lets you compare equal-weight,
minimum-variance, and mean-variance portfolios.

## Run locally

From the repo root:

```bash
streamlit run fins2026/week4/scratch/dff_walkthrough/app/streamlit_app.py
```

The app loads the course equity bundle automatically on first run (internet
connection required). No API keys or local files needed.

## What it does

- Pick any subset of the 50 stocks via the sidebar
- Choose unconstrained (short sales allowed) or long-only optimization
- View portfolio weights, growth of $1, the efficient frontier, and a
  scorecard
- All results are **in-sample** using the full 2020–2023 window

## Structure

```
app/
  streamlit_app.py   entrypoint
  app_config.py      tickers, sectors, colors, labels
  app_data.py        cached data loading and portfolio math
  app_insights.py    Plotly figures and formatting
  app_views.py       Streamlit layout, sidebar, tabs
  README.md
  tests/
    test_app_smoke.py
```

## No secrets

This app uses no API keys, no secrets, and no local paths. The data bundle
is fetched from a public Google Drive URL by `data_access.py`.
