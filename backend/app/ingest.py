"""Download wind actuals (FUELHH) and wind forecasts (WINDFOR) for the decision window.

Run:  python -m app.ingest
Writes data/actuals.csv and data/forecasts.csv (committed to the repo so the deployed
app never depends on the live Elexon API).
"""
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
from .config import BASE_URL, DATA_DIR, ACTUALS_CSV, FORECASTS_CSV, DECISION_START, DECISION_END

FMT = "%Y-%m-%dT%H:%MZ"


def _get(path: str, params: dict, retries: int = 4) -> list[dict]:
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE_URL}{path}", params=params, timeout=60,
                             headers={"Accept": "application/json"})
            r.raise_for_status()
            body = r.json()
            return body["data"] if isinstance(body, dict) else body
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def _windows(start: datetime, end: datetime, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def fetch_actuals(t_start: datetime, t_end: datetime) -> pd.DataFrame:
    rows = []
    for a, b in _windows(t_start, t_end, 7):
        rows += _get("/datasets/FUELHH/stream", {
            "settlementDateFrom": a.strftime("%Y-%m-%d"),
            "settlementDateTo": (b - timedelta(seconds=1)).strftime("%Y-%m-%d"),
            "fuelType": "WIND",
        })
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df[["startTime", "generation"]].drop_duplicates("startTime").sort_values("startTime")
    return df[(df.startTime >= t_start) & (df.startTime < t_end)]


def fetch_forecasts(p_start: datetime, p_end: datetime) -> pd.DataFrame:
    rows = []
    for a, b in _windows(p_start, p_end, 2):
        rows += _get("/datasets/WINDFOR/stream", {
            "publishDateTimeFrom": a.strftime(FMT),
            "publishDateTimeTo": b.strftime(FMT),
        })
    df = pd.DataFrame(rows)
    for c in ("startTime", "publishTime"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df = df[["startTime", "publishTime", "generation"]]
    return df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"])


def main():
    utc = timezone.utc
    d0 = datetime.fromisoformat(DECISION_START).replace(tzinfo=utc)
    d1 = datetime.fromisoformat(DECISION_END).replace(tzinfo=utc)
    t_start = d0 + timedelta(days=1)          # first delivery day  = 2 Jan
    t_end = d1 + timedelta(days=2)            # end of last delivery day = 1 Feb 24:00
    p_start = d0 - timedelta(days=2)          # include forecasts published just before
    p_end = d1 + timedelta(days=1)            # nothing after last decision is needed

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    act = fetch_actuals(t_start, t_end)
    act.to_csv(ACTUALS_CSV, index=False)
    print(f"actuals: {len(act)} rows -> {ACTUALS_CSV}")
    fc = fetch_forecasts(p_start, p_end)
    fc = fc[(fc.startTime >= t_start) & (fc.startTime < t_end)]
    fc.to_csv(FORECASTS_CSV, index=False)
    print(f"forecasts: {len(fc)} rows -> {FORECASTS_CSV}")


if __name__ == "__main__":
    main()
