"""SpaceX IPO (SPCX) performance analysis -- Weeks 1-3 toolkit.

Loads hourly and five-minute price data, computes growth-of-$1, annualised
volatility and Sharpe ratio, and compares against a live benchmark
(Invesco QQQ Trust).  Outputs figures and summary tables to output/.
"""

from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yfinance as yf

sns.set_theme(style="whitegrid")

OUTPUT = "output"
BENCH_TICKER = "QQQ"
RISK_FREE = 0.05
TRADING_HOURS_PER_YEAR = 6.5 * 252
TRADING_5MIN_PER_YEAR = 78 * 252
TRADING_DAYS_PER_YEAR = 252


def _ensure_datetime_column(df):
    if "datetime" not in df.columns:
        df = df.reset_index()
        df = df.rename(columns={"index": "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def load_data():
    hourly = _ensure_datetime_column(pd.read_parquet("spcx_hourly.parquet"))
    five_min = _ensure_datetime_column(pd.read_parquet("spcx_5min.parquet"))
    hourly["return"] = hourly["return"] / 100.0
    return hourly, five_min


def download_benchmark_daily(hourly):
    start = hourly["datetime"].min().strftime("%Y-%m-%d")
    end = hourly["datetime"].max().strftime("%Y-%m-%d")
    raw = yf.download(BENCH_TICKER, start=start, end=end, auto_adjust=True)
    if raw.empty:
        raise RuntimeError(f"Could not download {BENCH_TICKER}.")
    close = raw["Close"]
    bench = close.reset_index()
    bench = bench.rename(
        columns={bench.columns[0]: "date", bench.columns[1]: "close"}
    )
    bench["date"] = pd.to_datetime(bench["date"]).dt.tz_localize(None)
    bench["return"] = bench["close"].pct_change()
    return bench


def annualised_vol(returns, periods_per_year):
    return float(returns.std() * np.sqrt(periods_per_year) * 100)


def sharpe_ratio(returns, periods_per_year, rf):
    excess = returns - rf / periods_per_year
    return float(np.sqrt(periods_per_year) * excess.mean() / returns.std())


def max_drawdown(close):
    peak = close.expanding().max()
    dd = (close - peak) / peak
    return float(dd.min() * 100)


def daily_stats_from_hourly(hourly):
    daily = hourly.set_index("datetime").resample("D").agg({
        "close": "last",
        "return": lambda x: (1 + x).prod() - 1,
    })
    daily = daily.dropna(subset=["close"])
    daily["close"] = daily["close"].ffill()
    daily["return"] = daily["return"].fillna(0)
    return daily.reset_index()


def summary_stats(return_series, total_return, label, periods_per_year):
    ann_vol = annualised_vol(return_series, periods_per_year)
    sr = sharpe_ratio(return_series, periods_per_year, RISK_FREE)
    return {
        "Ticker": label,
        "Total Return (%)": round(total_return, 2),
        "Ann. Volatility (%)": round(ann_vol, 2),
        "Sharpe Ratio (rf=5%)": round(sr, 2),
    }


def plot_figures(hourly, bench_daily, five_min):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    # Top-left: SPCX hourly price
    ax = axes[0, 0]
    ax.plot(hourly["datetime"], hourly["close"], color="tab:blue", linewidth=1.5)
    ax.axhline(y=135.0, color="gray", linestyle="--", linewidth=0.8, label="IPO offer ($135)")
    ax.annotate(
        "IPO pop\n+22.2%",
        xy=(hourly["datetime"].iloc[1], hourly["close"].iloc[1]),
        xytext=(hourly["datetime"].iloc[4], hourly["close"].iloc[1] + 10),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=9,
    )
    ax.set_title("SPCX Hourly Close Price", fontsize=11)
    ax.set_ylabel("Price (USD)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30)
    ax.legend(fontsize=8)

    # Top-right: SPCX intraday growth of $1 (hourly path)
    ax = axes[0, 1]
    spcx_growth = hourly["close"] / hourly["close"].iloc[0]
    ax.plot(hourly["datetime"], spcx_growth, color="tab:blue", linewidth=1.5, label="SPCX")
    ax.set_title("Growth of $1 — SPCX (hourly)", fontsize=11)
    ax.set_ylabel("Wealth")
    ax.axhline(y=1.0, color="gray", linewidth=0.5, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30)
    ax.legend(fontsize=8)

    # Bottom-left: 5-min return histogram
    ax = axes[1, 0]
    rets = five_min["return"].dropna() * 100
    ax.hist(rets, bins=80, color="tab:blue", edgecolor="white", alpha=0.8)
    ax.axvline(rets.mean(), color="red", linestyle="--", linewidth=1,
               label=f"Mean: {rets.mean():.3f}%")
    ax.set_title("5-min Return Distribution", fontsize=11)
    ax.set_xlabel("Return (%)")
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=8)

    # Bottom-right: 5-min cumulative wealth
    ax = axes[1, 1]
    cum5 = (1 + five_min["return"]).cumprod()
    ax.plot(five_min["datetime"], cum5, color="tab:blue", linewidth=0.6)
    ax.set_title("5-min Cumulative Wealth (whole window)", fontsize=11)
    ax.set_ylabel("Wealth")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30)

    for ax_ in axes.flat:
        ax_.tick_params(labelsize=8)

    fig.savefig(f"{OUTPUT}/fig01_spcx_overview.png", dpi=200)
    plt.close(fig)
    print("  -> output/fig01_spcx_overview.png")

    # Figure 2: SPCX vs benchmark daily comparison
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)

    ax = axes[0]
    ax.plot(hourly["datetime"], hourly["close"], color="tab:blue", linewidth=1, label="SPCX")
    ax.set_title("SPCX Hourly Close", fontsize=10)
    ax.set_ylabel("Price (USD)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(bench_daily["date"], bench_daily["close"], color="tab:orange",
            linewidth=1.5, marker="o", markersize=4, label=BENCH_TICKER)
    ax.set_title(f"{BENCH_TICKER} Daily Close", fontsize=10)
    ax.set_ylabel("Price (USD)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.legend(fontsize=8)

    fig.savefig(f"{OUTPUT}/fig02_spcx_vs_benchmark_prices.png", dpi=200)
    plt.close(fig)
    print("  -> output/fig02_spcx_vs_benchmark_prices.png")

    # Figure 3: Rolling volatility
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)

    ax = axes[0]
    roll_vol = hourly["return"].rolling(5).std() * np.sqrt(TRADING_HOURS_PER_YEAR) * 100
    ax.plot(hourly["datetime"], roll_vol, color="tab:blue", linewidth=1)
    ax.set_title("SPCX Rolling 5-hr Ann. Volatility", fontsize=10)
    ax.set_ylabel("Ann. Volatility (%)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30, labelsize=8)

    ax = axes[1]
    roll_vol_b = bench_daily["return"].rolling(2).std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    ax.plot(bench_daily["date"], roll_vol_b, color="tab:orange", linewidth=1)
    ax.set_title(f"{BENCH_TICKER} Rolling 2-day Ann. Volatility", fontsize=10)
    ax.set_ylabel("Ann. Volatility (%)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=30, labelsize=8)

    fig.savefig(f"{OUTPUT}/fig03_volatility.png", dpi=200)
    plt.close(fig)
    print("  -> output/fig03_volatility.png")


def write_summary_table(stats_list):
    df = pd.DataFrame(stats_list)
    df = df.set_index("Ticker")
    df.to_csv(f"{OUTPUT}/table01_summary_stats.csv")
    print("  -> output/table01_summary_stats.csv")
    print("\n" + df.to_string() + "\n")


def main():
    print("=" * 60)
    print("SpaceX IPO (SPCX) Performance Analysis")
    print(f"Run: {datetime.now():%Y-%m-%d %H:%M}")
    print(f"Benchmark: {BENCH_TICKER} (live data)")
    print("=" * 60)

    hourly, five_min = load_data()
    print(f"\nHourly data: {len(hourly)} rows, "
          f"{hourly['datetime'].min():%Y-%m-%d} to {hourly['datetime'].max():%Y-%m-%d}")
    print(f"5-min data:  {len(five_min)} rows, "
          f"{five_min['datetime'].min():%Y-%m-%d} to {five_min['datetime'].max():%Y-%m-%d}")

    # Resample SPCX to daily for fair comparison
    spcx_daily = daily_stats_from_hourly(hourly)

    # Benchmark
    print(f"\nDownloading {BENCH_TICKER} daily …")
    bench_daily = download_benchmark_daily(hourly)
    print(f"  {len(bench_daily)} trading days")

    # Summary stats
    spcx_total_ret = (spcx_daily["close"].iloc[-1] / spcx_daily["close"].iloc[0] - 1) * 100
    bench_total_ret = (bench_daily["close"].iloc[-1] / bench_daily["close"].iloc[0] - 1) * 100

    print("\n--- Summary Statistics ---")
    stats = [
        summary_stats(
            spcx_daily["return"].dropna(), spcx_total_ret, "SPCX",
            TRADING_DAYS_PER_YEAR,
        ),
        summary_stats(
            bench_daily["return"].dropna(), bench_total_ret, BENCH_TICKER,
            TRADING_DAYS_PER_YEAR,
        ),
    ]

    # Also compute on hourly basis for SPCX
    spcx_total_ret_h = (hourly["close"].iloc[-1] / hourly["close"].iloc[0] - 1) * 100
    stats_h = summary_stats(
        hourly["return"].dropna(), spcx_total_ret_h, "SPCX (hourly)", TRADING_HOURS_PER_YEAR
    )
    stats.append(stats_h)

    write_summary_table(stats)

    # Figures
    print("--- Generating Figures ---")
    plot_figures(hourly, bench_daily, five_min)

    print("\nDone. All outputs in output/")


if __name__ == "__main__":
    main()
