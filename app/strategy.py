from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from .data import rolling_ols_beta, static_ols_beta
from .stats import compute_pair_stats


@dataclass
class BacktestConfig:
    lookback: int
    entry_z: float
    exit_z: float
    stop_z: float
    cost_bps: float
    slippage_bps: float
    capital: float
    use_rolling_beta: bool


@dataclass
class BacktestResult:
    pair_stats: Dict[str, float]
    metrics: Dict[str, float]
    timeseries: Dict[str, List]
    trades: List[Dict]


def _annualized_return(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    total = equity.iloc[-1] / equity.iloc[0] - 1.0
    years = len(equity) / 252.0
    if years <= 0:
        return 0.0
    return float((1.0 + total) ** (1.0 / years) - 1.0)


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def _sharpe(returns: pd.Series) -> float:
    vol = returns.std()
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float((returns.mean() / vol) * np.sqrt(252.0))


def run_backtest(prices: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
    px = prices.copy()

    if config.use_rolling_beta:
        beta = rolling_ols_beta(px["A"], px["B"], config.lookback)
    else:
        beta_val = static_ols_beta(px["A"], px["B"])
        beta = pd.Series(beta_val, index=px.index)

    spread = px["A"] - beta * px["B"]
    spread_mu = spread.rolling(config.lookback).mean()
    spread_sigma = spread.rolling(config.lookback).std().replace(0.0, np.nan)
    zscore = (spread - spread_mu) / spread_sigma

    signal = pd.Series(0, index=px.index, dtype=float)
    position = 0
    entry_info = None
    trades: List[Dict] = []

    for i in range(1, len(px)):
        z = zscore.iloc[i - 1]
        dt = px.index[i]

        if np.isnan(z):
            signal.iloc[i] = position
            continue

        if position == 0:
            if z > config.entry_z:
                position = -1
                entry_info = {"entry_date": str(dt.date()), "entry_z": float(z), "side": "short_spread"}
            elif z < -config.entry_z:
                position = 1
                entry_info = {"entry_date": str(dt.date()), "entry_z": float(z), "side": "long_spread"}
        else:
            stop_hit = abs(z) >= config.stop_z
            mean_revert_exit = (position == 1 and z >= config.exit_z) or (position == -1 and z <= config.exit_z)

            if stop_hit or mean_revert_exit:
                exit_info = {
                    "exit_date": str(dt.date()),
                    "exit_z": float(z),
                    "exit_reason": "stop" if stop_hit else "mean_revert",
                }
                if entry_info:
                    trades.append({**entry_info, **exit_info})
                position = 0
                entry_info = None

        signal.iloc[i] = position

    ret_a = px["A"].pct_change().fillna(0.0)
    ret_b = px["B"].pct_change().fillna(0.0)
    beta_shifted = beta.shift(1).fillna(beta)

    gross_daily = signal.shift(1).fillna(0.0) * (ret_a - beta_shifted * ret_b)

    turnover = signal.diff().abs().fillna(0.0)
    total_cost_rate = (config.cost_bps + config.slippage_bps) / 10000.0
    costs = turnover * total_cost_rate
    net_daily = gross_daily - costs

    equity = (1.0 + net_daily).cumprod() * config.capital

    wins = 0
    closed = 0
    if trades:
        spread_ret = spread.pct_change().fillna(0.0)
        trade_series = signal.shift(1).fillna(0.0) * spread_ret
        for tr in trades:
            mask = (px.index >= pd.to_datetime(tr["entry_date"])) & (px.index <= pd.to_datetime(tr["exit_date"]))
            tr_ret = trade_series.loc[mask].sum()
            tr["trade_return"] = float(tr_ret)
            closed += 1
            wins += int(tr_ret > 0)

    stats = compute_pair_stats(px["A"], px["B"], spread)

    metrics = {
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
        "annual_return": _annualized_return(equity),
        "annual_volatility": float(net_daily.std() * np.sqrt(252.0)),
        "sharpe_ratio": _sharpe(net_daily),
        "max_drawdown": _max_drawdown(equity),
        "win_rate": float(wins / closed) if closed else 0.0,
        "num_trades": float(closed),
        "avg_turnover": float(turnover.mean()),
        "cost_drag": float(costs.sum()),
    }

    pair_stats = {
        "correlation": stats.correlation,
        "cointegration_pvalue": stats.coint_pvalue,
        "spread_adf_pvalue": stats.adf_pvalue,
        "half_life_days": stats.half_life_days,
        "beta_mean": float(beta.mean()),
    }

    timeseries = {
        "dates": [str(d.date()) for d in px.index],
        "price_a": [float(x) for x in px["A"].values],
        "price_b": [float(x) for x in px["B"].values],
        "beta": [float(x) if pd.notna(x) else None for x in beta.values],
        "spread": [float(x) if pd.notna(x) else None for x in spread.values],
        "zscore": [float(x) if pd.notna(x) else None for x in zscore.values],
        "signal": [float(x) for x in signal.values],
        "equity": [float(x) for x in equity.values],
        "returns": [float(x) for x in net_daily.values],
    }

    return BacktestResult(pair_stats=pair_stats, metrics=metrics, timeseries=timeseries, trades=trades)
