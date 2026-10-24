"""Central configuration. All timestamps are UTC (== UK local time in January)."""
from pathlib import Path
import os

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
ACTUALS_CSV = DATA_DIR / "actuals.csv"
FORECASTS_CSV = DATA_DIR / "forecasts.csv"

# Purchase decisions are made in January 2026 (decision day D), for delivery day D+1.
DECISION_START = "2026-01-01"
DECISION_END = "2026-01-31"

# Default decision cutoff on day D (HH:MM, UTC). Day-ahead auction gate closure is
# ~09:20 UK time, so 09:00 is the last "clean" moment to have seen a forecast.
DEFAULT_CUTOFF = "09:00"
