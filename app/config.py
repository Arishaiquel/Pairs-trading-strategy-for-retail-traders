from __future__ import annotations

DEFAULT_PAIRS = [
    ("KO", "PEP"),
    ("MA", "V"),
    ("XOM", "CVX"),
    ("SPY", "IVV"),
    ("GLD", "IAU"),
]

DEFAULTS = {
    "start_date": "2018-01-01",
    "end_date": "2026-01-01",
    "lookback": 60,
    "entry_z": 2.0,
    "exit_z": 0.0,
    "stop_z": 3.5,
    "cost_bps": 5.0,
    "slippage_bps": 2.0,
    "capital": 100000.0,
    "use_rolling_beta": True,
    "use_rolling_cointegration": False,
}
