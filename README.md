# Pairs Trading Lab

End-to-end pairs trading system with a browser frontend and a Python backtesting engine.

## Features
- Pair selection with example universe (`KO/PEP`, `MA/V`, `XOM/CVX`, `SPY/IVV`, `GLD/IAU`)
- Correlation and cointegration diagnostics
- Spread model: `A - beta * B` with static or rolling beta
- Signal engine using z-score thresholds
- Transaction cost and slippage model (bps)
- Backtest metrics: total return, annual return, annual volatility, Sharpe, max drawdown, win rate
- Trade blotter and interactive charts

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## API
- `GET /api/defaults`
- `POST /api/backtest`

Example payload:
```json
{
  "ticker_a": "KO",
  "ticker_b": "PEP",
  "start_date": "2018-01-01",
  "end_date": "2026-01-01",
  "lookback": 60,
  "entry_z": 2.0,
  "exit_z": 0.0,
  "stop_z": 3.5,
  "cost_bps": 5,
  "slippage_bps": 2,
  "capital": 100000,
  "use_rolling_beta": true
}
```

## Notes
- This is a research backtester, not production execution software.
- Data comes from Yahoo Finance via `yfinance`.
