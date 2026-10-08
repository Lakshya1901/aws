"""Fast checks of analysis/backtest.py building blocks on synthetic data."""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "analysis"))
import backtest  # noqa: E402

TH = backtest.PARAMS["thresholds"]


def test_baseline_uses_prior_years_only():
    idx = pd.date_range("2023-01-01", "2024-12-31")
    a = pd.Series(np.where(idx.year == 2023, 100.0, 500.0), index=idx)
    b = backtest.baseline(a)
    assert b["2023-06-01"] != b["2023-06-01"]  # NaN: no prior year
    assert b["2024-06-01"] == 100.0


def test_missing_days_stay_missing_and_need_5_of_7():
    idx = pd.date_range("2023-01-01", "2024-12-31")
    arr = pd.DataFrame({"m": 100.0}, index=idx)
    arr.loc["2024-06-01":"2024-06-03", "m"] = np.nan
    price = pd.DataFrame({"m": 10.0}, index=idx)
    R, dP, B, level = backtest.risk(arr, price, TH)
    assert level.at[pd.Timestamp("2024-06-03"), "m"] == "unknown"  # 4 of last 7 days
    assert level.at[pd.Timestamp("2024-06-02"), "m"] == "safe"  # 5 of last 7 days
    assert R.at[pd.Timestamp("2024-06-02"), "m"] == 1.0  # missing days not counted as zero


def test_level_rule():
    R = pd.DataFrame({"m": [1.0, 1.3, 2.0, 1.6, 1.0]})
    dP = pd.DataFrame({"m": [0.0, 0.0, 0.0, -0.3, -0.2]})
    assert list(backtest.level_of(R, dP, TH)["m"]) == ["safe", "watch", "glut", "glut", "watch"]


def test_crash_days():
    p = pd.DataFrame({"m": [10.0, 10.0, 10.0, 7.0, 4.0, np.nan]})
    assert list(backtest.crash_days(p)["m"]) == [False, False, False, True, True, False]
