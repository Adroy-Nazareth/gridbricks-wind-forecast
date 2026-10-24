import pandas as pd
from app import analysis as A

def ts(s): return pd.Timestamp(s, tz="UTC")

def fc_frame():
    return pd.DataFrame({
        "startTime":   [ts("2026-01-05 12:00")] * 3,
        "publishTime": [ts("2026-01-04 06:00"), ts("2026-01-04 08:59"), ts("2026-01-04 09:01")],
        "generation":  [100.0, 200.0, 300.0]})

def test_picks_latest_before_cutoff_and_ignores_later():
    sel = A.select_forecasts(fc_frame(), "09:00")
    assert len(sel) == 1 and sel.forecast.iloc[0] == 200.0

def test_cutoff_is_inclusive_and_changes_result():
    assert A.select_forecasts(fc_frame(), "09:01").forecast.iloc[0] == 300.0
    assert A.select_forecasts(fc_frame(), "07:00").forecast.iloc[0] == 100.0

def test_target_without_eligible_forecast_dropped():
    assert A.select_forecasts(fc_frame(), "05:00").empty

def test_error_sign_and_metrics():
    sel = A.select_forecasts(fc_frame(), "09:00")
    act = pd.DataFrame({"startTime": [ts("2026-01-05 12:00")], "generation": [250.0]})
    df = A.join_actuals(sel, act)
    s = A.summary(df)
    assert df.error.iloc[0] == -50.0            # forecast < actual => negative
    assert s["mae"] == 50.0 and s["rmse"] == 50.0 and s["bias"] == -50.0

def test_buy_buffer_only_penalises_overforecast():
    df = pd.DataFrame({"forecast": [100.0, 100.0], "error": [-10.0, -20.0]})
    assert A.buy_buffer(df, 500)["shortfall_buffer_mw"] == 0.0
