from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint


@dataclass
class PairStats:
    correlation: float
    coint_pvalue: float
    adf_pvalue: float
    half_life_days: float


def estimate_half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    if len(s) < 20:
        return float("nan")

    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    aligned = pd.concat([lag, delta], axis=1).dropna()
    if aligned.empty:
        return float("nan")

    x = aligned.iloc[:, 0].values
    y = aligned.iloc[:, 1].values

    x_mean = x.mean()
    y_mean = y.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return float("nan")

    beta = np.sum((x - x_mean) * (y - y_mean)) / denom
    if beta >= 0:
        return float("inf")

    half_life = -np.log(2) / beta
    return float(max(1.0, half_life))


def compute_pair_stats(series_a: pd.Series, series_b: pd.Series, spread: pd.Series) -> PairStats:
    corr = float(series_a.corr(series_b))
    coint_p = float(coint(series_a, series_b)[1])

    try:
        adf_p = float(adfuller(spread.dropna(), autolag="AIC")[1])
    except ValueError:
        adf_p = float("nan")

    half_life = estimate_half_life(spread)
    return PairStats(correlation=corr, coint_pvalue=coint_p, adf_pvalue=adf_p, half_life_days=half_life)
