from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import DEFAULTS, DEFAULT_PAIRS
from .data import fetch_pair_prices
from .strategy import BacktestConfig, run_backtest

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Pairs Trading Lab", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class BacktestRequest(BaseModel):
    ticker_a: str = Field(..., min_length=1, max_length=12)
    ticker_b: str = Field(..., min_length=1, max_length=12)
    start_date: str = DEFAULTS["start_date"]
    end_date: str = DEFAULTS["end_date"]
    lookback: int = Field(DEFAULTS["lookback"], ge=20, le=252)
    entry_z: float = Field(DEFAULTS["entry_z"], gt=0.1, le=5)
    exit_z: float = Field(DEFAULTS["exit_z"], ge=-2, le=2)
    stop_z: float = Field(DEFAULTS["stop_z"], gt=0.5, le=8)
    cost_bps: float = Field(DEFAULTS["cost_bps"], ge=0, le=200)
    slippage_bps: float = Field(DEFAULTS["slippage_bps"], ge=0, le=200)
    capital: float = Field(DEFAULTS["capital"], gt=100)
    use_rolling_beta: bool = DEFAULTS["use_rolling_beta"]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_path = BASE_DIR / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.get("/api/defaults")
def get_defaults() -> Dict:
    return {"defaults": DEFAULTS, "example_pairs": DEFAULT_PAIRS}


def _build_config(payload: BacktestRequest) -> BacktestConfig:
    return BacktestConfig(
        lookback=payload.lookback,
        entry_z=payload.entry_z,
        exit_z=payload.exit_z,
        stop_z=payload.stop_z,
        cost_bps=payload.cost_bps,
        slippage_bps=payload.slippage_bps,
        capital=payload.capital,
        use_rolling_beta=payload.use_rolling_beta,
    )


@app.post("/api/backtest")
def backtest(payload: BacktestRequest) -> Dict:
    if payload.ticker_a.upper() == payload.ticker_b.upper():
        raise HTTPException(status_code=400, detail="Tickers must be different")

    try:
        pair = fetch_pair_prices(
            payload.ticker_a.upper(),
            payload.ticker_b.upper(),
            payload.start_date,
            payload.end_date,
        )
        config = _build_config(payload)

        result = run_backtest(pair.prices, config)
        return {
            "pair": {"ticker_a": pair.ticker_a, "ticker_b": pair.ticker_b},
            "pair_stats": result.pair_stats,
            "metrics": result.metrics,
            "timeseries": result.timeseries,
            "trades": result.trades,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}") from exc


@app.post("/api/scan")
def scan_pairs(payload: BacktestRequest) -> Dict[str, List[Dict]]:
    config = _build_config(payload)
    rows: List[Dict] = []
    for ticker_a, ticker_b in DEFAULT_PAIRS:
        try:
            pair = fetch_pair_prices(
                ticker_a,
                ticker_b,
                payload.start_date,
                payload.end_date,
            )
            result = run_backtest(pair.prices, config)
            rows.append(
                {
                    "pair": f"{ticker_a}/{ticker_b}",
                    "correlation": result.pair_stats["correlation"],
                    "cointegration_pvalue": result.pair_stats["cointegration_pvalue"],
                    "half_life_days": result.pair_stats["half_life_days"],
                    "annual_return": result.metrics["annual_return"],
                    "sharpe_ratio": result.metrics["sharpe_ratio"],
                    "max_drawdown": result.metrics["max_drawdown"],
                }
            )
        except Exception:
            continue

    rows.sort(key=lambda x: (x["cointegration_pvalue"], -x["sharpe_ratio"]))
    return {"results": rows}
