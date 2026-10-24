import re
from functools import lru_cache
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from . import analysis as A
from .config import ACTUALS_CSV, FORECASTS_CSV, DEFAULT_CUTOFF

app = FastAPI(title="Wind Forecast Accuracy API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not ACTUALS_CSV.exists() or not FORECASTS_CSV.exists():
        raise HTTPException(503, "Data not found. Run `python -m app.ingest` first.")
    act = pd.read_csv(ACTUALS_CSV, parse_dates=["startTime"])
    fc = pd.read_csv(FORECASTS_CSV, parse_dates=["startTime", "publishTime"])
    for d in (act, fc):
        d["startTime"] = pd.to_datetime(d["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    return act, fc


def _frame(cutoff: str, start: str | None, end: str | None) -> pd.DataFrame:
    if not CUTOFF_RE.match(cutoff):
        raise HTTPException(422, "cutoff must be HH:MM (UTC)")
    act, fc = load()
    df = A.join_actuals(A.select_forecasts(fc, cutoff), act)
    if start:
        df = df[df["startTime"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["startTime"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return df


Cutoff = Query(DEFAULT_CUTOFF, description="Decision cutoff on day D, HH:MM UTC")


@app.get("/api/meta")
def meta():
    act, fc = load()
    return {"actuals_rows": len(act), "forecast_rows": len(fc),
            "first_target": act.startTime.min(), "last_target": act.startTime.max(),
            "first_publish": fc.publishTime.min(), "last_publish": fc.publishTime.max(),
            "default_cutoff": DEFAULT_CUTOFF}


@app.get("/api/forecast")
def forecast(cutoff: str = Cutoff, start: str | None = None, end: str | None = None):
    df = _frame(cutoff, start, end)
    return {"cutoff": cutoff, "points": df.assign(
        startTime=df.startTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        publishTime=df.publishTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )[["startTime", "publishTime", "forecast", "actual", "error", "horizon_h"]].to_dict("records")}


@app.get("/api/metrics")
def metrics(cutoff: str = Cutoff, start: str | None = None, end: str | None = None):
    df = _frame(cutoff, start, end)
    return {"cutoff": cutoff, "summary": A.summary(df), "by_hour": A.by_hour(df),
            "by_day": A.by_day(df), "histogram": A.histogram(df)}


@app.get("/api/horizon")
def horizon(bucket_h: int = Query(6, ge=1, le=24)):
    act, fc = load()
    return {"bucket_h": bucket_h, "curve": A.horizon_curve(fc, act, bucket_h)}


@app.get("/api/buy")
def buy(demand_mw: float = Query(..., gt=0), cutoff: str = Cutoff,
        quantile: float = Query(0.95, gt=0.5, lt=1), start: str | None = None, end: str | None = None):
    return A.buy_buffer(_frame(cutoff, start, end), demand_mw, quantile)


@app.get("/api/health")
def health():
    return {"status": "ok"}
