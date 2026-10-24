"""Pure analysis functions (no I/O) so they are easy to unit test.

Key idea: a buyer deciding on day D for delivery day D+1 can only use forecasts with
publishTime <= cutoff(D). For each target startTime we keep the LATEST such forecast.
"""
import numpy as np
import pandas as pd


def select_forecasts(fc: pd.DataFrame, cutoff: str = "09:00") -> pd.DataFrame:
    """Latest forecast per target half-hour published at/before cutoff on the previous day."""
    hh, mm = (int(x) for x in cutoff.split(":"))
    d = fc.copy()
    day_before = d["startTime"].dt.normalize() - pd.Timedelta(days=1)
    d["cutoff_dt"] = day_before + pd.Timedelta(hours=hh, minutes=mm)
    d = d[d["publishTime"] <= d["cutoff_dt"]]
    d = d.sort_values(["startTime", "publishTime"]).groupby("startTime", as_index=False).last()
    d["horizon_h"] = (d["startTime"] - d["publishTime"]).dt.total_seconds() / 3600
    return d[["startTime", "publishTime", "generation", "horizon_h"]].rename(
        columns={"generation": "forecast"})


def join_actuals(sel: pd.DataFrame, act: pd.DataFrame) -> pd.DataFrame:
    df = sel.merge(act.rename(columns={"generation": "actual"}), on="startTime", how="inner")
    df["error"] = df["forecast"] - df["actual"]          # +ve = over-forecast
    df["abs_error"] = df["error"].abs()
    return df


def summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    e, a = df["error"], df["actual"]
    nz = a > 0
    return {
        "n": int(len(df)),
        "mae": float(e.abs().mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "bias": float(e.mean()),
        "mape": float((e[nz].abs() / a[nz]).mean() * 100) if nz.any() else None,
        "nmae_pct": float(e.abs().mean() / a.mean() * 100) if a.mean() else None,
        "mean_actual": float(a.mean()),
        "p10": float(e.quantile(0.10)), "p50": float(e.quantile(0.50)),
        "p90": float(e.quantile(0.90)),
        "abs_p90": float(e.abs().quantile(0.90)), "abs_p95": float(e.abs().quantile(0.95)),
        "under_forecast_p95": float(-e.quantile(0.05)),   # MW shortfall risk (actual > forecast)
        "over_forecast_p95": float(e.quantile(0.95)),     # MW surplus risk
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df["startTime"].dt.hour)
    out = g.agg(mae=("abs_error", "mean"), bias=("error", "mean"),
                rmse=("error", lambda s: float(np.sqrt((s ** 2).mean())))).reset_index()
    return out.rename(columns={"startTime": "hour"}).to_dict("records")


def by_day(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(df["startTime"].dt.strftime("%Y-%m-%d"))
    out = g.agg(mae=("abs_error", "mean"), bias=("error", "mean"),
                mean_actual=("actual", "mean")).reset_index()
    return out.rename(columns={"startTime": "day"}).to_dict("records")


def histogram(df: pd.DataFrame, bins: int = 30) -> list[dict]:
    if df.empty:
        return []
    counts, edges = np.histogram(df["error"], bins=bins)
    return [{"from": float(edges[i]), "to": float(edges[i + 1]), "count": int(c)}
            for i, c in enumerate(counts)]


def horizon_curve(fc: pd.DataFrame, act: pd.DataFrame, bucket_h: int = 6) -> list[dict]:
    """Error vs lead time using ALL published forecasts (not just the selected one)."""
    d = fc.merge(act.rename(columns={"generation": "actual"}), on="startTime")
    d["horizon_h"] = (d["startTime"] - d["publishTime"]).dt.total_seconds() / 3600
    d = d[d["horizon_h"] >= 0]
    d["err"] = d["generation"] - d["actual"]
    d["bucket"] = (d["horizon_h"] // bucket_h * bucket_h).astype(int)
    g = d.groupby("bucket").agg(mae=("err", lambda s: s.abs().mean()),
                                bias=("err", "mean"), n=("err", "size")).reset_index()
    return g.to_dict("records")


def buy_buffer(df: pd.DataFrame, demand_mw: float, quantile: float = 0.95) -> dict:
    """Illustrative, wind-only: extra power to buy so the plan survives a bad forecast.

    error = forecast - actual, so a POSITIVE error means wind under-delivered versus the
    forecast. The buffer is the `quantile` of that error (floored at 0).
    """
    buffer_mw = max(float(df["error"].quantile(quantile)), 0.0)
    base = (demand_mw - df["forecast"]).clip(lower=0)
    safe = (demand_mw - df["forecast"] + buffer_mw).clip(lower=0)
    return {"quantile": quantile, "shortfall_buffer_mw": buffer_mw,
            "avg_residual_mw": float(base.mean()),
            "avg_residual_with_buffer_mw": float(safe.mean())}
