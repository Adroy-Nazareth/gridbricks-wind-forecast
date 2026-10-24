"""Synthetic data in the same schema as Elexon, ONLY for tests/offline dev."""
import numpy as np, pandas as pd

def make(dir_, seed=0):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2026-01-02", "2026-02-01 23:30", freq="30min", tz="UTC")
    actual = 6000 + 3000 * np.sin(np.arange(len(t)) / 90) + rng.normal(0, 300, len(t))
    act = pd.DataFrame({"startTime": t, "generation": actual.clip(0)})
    rows = []
    for st, a in zip(t, act.generation):
        for lead_h in range(1, 49, 3):                       # forecasts every 3h up to 48h out
            pt = st - pd.Timedelta(hours=lead_h)
            rows.append((st, pt, max(a + rng.normal(0, 40 * lead_h), 0)))  # error grows w/ lead
    fc = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
    dir_.mkdir(parents=True, exist_ok=True)
    act.to_csv(dir_ / "actuals.csv", index=False); fc.to_csv(dir_ / "forecasts.csv", index=False)
