import importlib, pathlib
from fastapi.testclient import TestClient
from tests.make_synthetic import make

def client(tmp_path, monkeypatch):
    make(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.config, app.main
    importlib.reload(app.config); importlib.reload(app.main)
    return TestClient(app.main.app)

def test_endpoints(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.get("/api/health").json()["status"] == "ok"
    m = c.get("/api/metrics?cutoff=09:00").json()
    assert m["summary"]["n"] > 1000 and m["summary"]["mae"] > 0
    assert len(m["by_hour"]) == 24
    assert c.get("/api/metrics?cutoff=25:99").status_code == 422
    h = c.get("/api/horizon").json()["curve"]
    assert h[0]["mae"] < h[-1]["mae"]            # error grows with lead time
    assert c.get("/api/buy?demand_mw=20000").status_code == 200
    f = c.get("/api/forecast?start=2026-01-10&end=2026-01-10").json()["points"]
    assert len(f) == 48
