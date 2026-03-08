from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class PairData:
    ticker_a: str
    ticker_b: str
    prices: pd.DataFrame


def fetch_pair_prices(ticker_a: str, ticker_b: str, start_date: str, end_date: str) -> PairData:
    tickers = [ticker_a, ticker_b]
    raw = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if raw.empty:
        raise ValueError("No price data returned. Check ticker symbols and date range.")

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].copy()
    else:
        prices = raw.to_frame(name=ticker_a)

    prices = prices.rename(columns={ticker_a: "A", ticker_b: "B"})
    missing_cols = {"A", "B"} - set(prices.columns)
    if missing_cols:
        raise ValueError(f"Missing data columns: {sorted(missing_cols)}")

    prices = prices[["A", "B"]].dropna()
    if len(prices) < 120:
        raise ValueError("Not enough overlapping history for a robust backtest.")

    return PairData(ticker_a=ticker_a, ticker_b=ticker_b, prices=prices)


def rolling_ols_beta(series_a: pd.Series, series_b: pd.Series, lookback: int) -> pd.Series:
    cov = series_a.rolling(lookback).cov(series_b)
    var = series_b.rolling(lookback).var()
    beta = cov / var.replace(0.0, np.nan)
    return beta.ffill().bfill()


def static_ols_beta(series_a: pd.Series, series_b: pd.Series) -> float:
    x = series_b.values
    y = series_a.values
    x_mean = x.mean()
    y_mean = y.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return 1.0
    return float(np.sum((x - x_mean) * (y - y_mean)) / denom)
