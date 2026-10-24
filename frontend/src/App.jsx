import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "/api/forecast";

function formatMW(value) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${Math.round(value).toLocaleString("en-GB")} MW`;
}

function formatDate(value) {
  return new Date(value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  });
}

function MetricCard({ label, value, note, icon }) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </div>
  );
}

function ForecastChart({ points }) {
  const chart = useMemo(() => {
    const valid = points.filter(
      (p) => Number.isFinite(p.forecast) && Number.isFinite(p.actual)
    );

    if (!valid.length) return null;

    // Keep the chart readable while preserving the overall trend.
    const limit = 100;
    const sampled = valid.filter(
      (_, i) => i % Math.max(1, Math.ceil(valid.length / limit)) === 0
    );

    const values = sampled.flatMap((p) => [p.forecast, p.actual]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const width = 900;
    const height = 300;
    const pad = { top: 20, right: 18, bottom: 36, left: 58 };

    const x = (i) =>
      pad.left +
      (i / Math.max(1, sampled.length - 1)) *
        (width - pad.left - pad.right);

    const y = (value) =>
      pad.top +
      ((max - value) / range) * (height - pad.top - pad.bottom);

    const path = (key) =>
      sampled
        .map(
          (p, i) =>
            `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p[key]).toFixed(1)}`
        )
        .join(" ");

    return {
      sampled,
      width,
      height,
      pad,
      min,
      max,
      x,
      y,
      forecastPath: path("forecast"),
      actualPath: path("actual"),
    };
  }, [points]);

  if (!chart) {
    return <div className="empty-chart">No matching forecast and actual data.</div>;
  }

  const ticks = Array.from({ length: 5 }, (_, i) =>
    chart.min + ((chart.max - chart.min) * i) / 4
  );

  return (
    <div className="chart-wrap">
      <svg
        className="forecast-chart"
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        role="img"
        aria-label="Wind generation forecast compared with actual generation"
      >
        {ticks.map((tick, i) => {
          const y = chart.y(tick);
          return (
            <g key={i}>
              <line
                x1={chart.pad.left}
                y1={y}
                x2={chart.width - chart.pad.right}
                y2={y}
                className="grid-line"
              />
              <text x={chart.pad.left - 10} y={y + 4} className="axis-label" textAnchor="end">
                {(tick / 1000).toFixed(0)}k
              </text>
            </g>
          );
        })}

        <path d={chart.forecastPath} className="forecast-line" />
        <path d={chart.actualPath} className="actual-line" />

        {[0, Math.floor((chart.sampled.length - 1) / 2), chart.sampled.length - 1]
          .filter((value, index, array) => array.indexOf(value) === index)
          .map((index) => (
            <text
              key={index}
              x={chart.x(index)}
              y={chart.height - 10}
              textAnchor={index === 0 ? "start" : index === chart.sampled.length - 1 ? "end" : "middle"}
              className="axis-label"
            >
              {formatDate(chart.sampled[index].startTime)}
            </text>
          ))}
      </svg>
    </div>
  );
}

export default function App() {
  const [cutoff, setCutoff] = useState("09:00");
  const [allPoints, setAllPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadForecast() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(
          `${API_URL}?cutoff=${encodeURIComponent(cutoff)}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || `Request failed (${response.status})`);
        }

        const data = await response.json();
        const points = Array.isArray(data) ? data : data.points;

        if (!Array.isArray(points)) {
          throw new Error("The API response did not contain a points array.");
        }

        setAllPoints(points);
        setLastUpdated(new Date());
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(
            `${err.message}. Check that the FastAPI backend is running on port 8000.`
          );
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    loadForecast();
    return () => controller.abort();
  }, [cutoff]);

  const points = useMemo(
    () =>
      allPoints.filter(
        (p) =>
          typeof p.startTime === "string" &&
          p.startTime.startsWith("2026-01") &&
          Number.isFinite(Number(p.forecast)) &&
          Number.isFinite(Number(p.actual))
      ),
    [allPoints]
  );

  const metrics = useMemo(() => {
    if (!points.length) return { mae: null, rmse: null, bias: null };

    const errors = points.map((p) => Number(p.forecast) - Number(p.actual));
    const mae = errors.reduce((sum, value) => sum + Math.abs(value), 0) / errors.length;
    const rmse = Math.sqrt(
      errors.reduce((sum, value) => sum + value * value, 0) / errors.length
    );
    const bias = errors.reduce((sum, value) => sum + value, 0) / errors.length;

    return { mae, rmse, bias };
  }, [points]);

  const latest = points[points.length - 1];
  const meanActual = points.length
    ? points.reduce((sum, p) => sum + Number(p.actual), 0) / points.length
    : null;

  const biasText =
    metrics.bias == null
      ? "Awaiting data"
      : Math.abs(metrics.bias) < 0.5
        ? "Near-zero average bias"
        : metrics.bias > 0
          ? "Forecasts overestimated generation"
          : "Forecasts underestimated generation";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">W</div>
          <div>
            <div className="brand-name">WindScope</div>
            <div className="brand-caption">ENERGY INTELLIGENCE</div>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active"><span>◫</span> Forecast overview</div>
        <div className="nav-item"><span>⌁</span> Accuracy analysis</div>
        <div className="nav-item"><span>◷</span> Decision timeline</div>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <div>
            <strong>Data workspace</strong>
            <span>UK wind generation</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> Forecast overview</div>
          <div className="topbar-right">
            <span className="live-dot" />
            Historical analysis
            <div className="avatar">WS</div>
          </div>
        </header>

        <section className="page-heading">
          <div>
            <div className="eyebrow">UK ELECTRICITY MARKET · BMRS DATA</div>
            <h1>Wind forecast intelligence</h1>
            <p className="page-subtitle">
              Understand forecast accuracy before day-ahead operational decisions.
            </p>
          </div>

          <div className="control-panel">
            <label htmlFor="cutoff">Decision cutoff (UTC)</label>
            <select id="cutoff" value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
              <option value="07:00">07:00 UTC</option>
              <option value="08:00">08:00 UTC</option>
              <option value="09:00">09:00 UTC</option>
              <option value="10:00">10:00 UTC</option>
              <option value="11:00">11:00 UTC</option>
              <option value="12:00">12:00 UTC</option>
            </select>
          </div>
        </section>

        <section className="period-banner">
          <div className="period-icon">↗</div>
          <div>
            <strong>January 2026 · Historical review</strong>
            <p>Forecasts are evaluated against recorded wind generation for the same target periods.</p>
          </div>
          <span className="period-tag">DAY-AHEAD VIEW</span>
        </section>

        {error && (
          <div className="error-banner">
            <strong>Unable to load data</strong>
            <p>{error}</p>
            <button onClick={() => setCutoff((value) => value)}>Retry</button>
          </div>
        )}

        <section className="metrics-grid">
          <MetricCard
            label="Mean absolute error"
            value={loading ? "Loading…" : formatMW(metrics.mae)}
            note="Average size of forecast error"
            icon="↔"
          />
          <MetricCard
            label="Root mean square error"
            value={loading ? "Loading…" : formatMW(metrics.rmse)}
            note="Penalises larger forecast misses"
            icon="⌁"
          />
          <MetricCard
            label="Mean forecast bias"
            value={loading ? "Loading…" : formatMW(metrics.bias)}
            note={biasText}
            icon="±"
          />
          <MetricCard
            label="Matched intervals"
            value={loading ? "…" : points.length.toLocaleString("en-GB")}
            note="January 2026 hourly observations"
            icon="◷"
          />
        </section>

        <section className="content-grid">
          <div className="panel chart-panel">
            <div className="panel-heading">
              <div>
                <h2>Forecast vs actual generation</h2>
                <p>Hourly wind generation · MW</p>
              </div>
              <span className="subtle-pill">JAN 2026</span>
            </div>

            <div className="legend">
              <span><i className="legend-line forecast-key" /> Day-ahead forecast</span>
              <span><i className="legend-line actual-key" /> Actual generation</span>
            </div>

            {loading ? (
              <div className="empty-chart">Loading forecast data…</div>
            ) : (
              <ForecastChart points={points} />
            )}

            <div className="chart-footnote">
              <span>Source: Elexon BMRS · WIND</span>
              <span>All times shown in UTC</span>
            </div>
          </div>

          <div className="panel insight-panel">
            <div className="panel-heading">
              <div>
                <h2>Operational signals</h2>
                <p>What the selected period tells you</p>
              </div>
              <span className="insight-symbol">✳</span>
            </div>

            <div className="insight-block">
              <span className="insight-label">AVERAGE ACTUAL GENERATION</span>
              <strong>{loading ? "Loading…" : formatMW(meanActual)}</strong>
              <p>Average recorded wind generation across matched January intervals.</p>
            </div>

            <div className="insight-divider" />

            <div className="insight-block">
              <span className="insight-label">DIRECTIONAL BIAS</span>
              <strong className="insight-copy">
                {loading ? "Loading…" : metrics.bias == null ? "Not available" : metrics.bias > 0 ? "Overforecast" : metrics.bias < 0 ? "Underforecast" : "Balanced"}
              </strong>
              <p>Positive bias means forecast generation was higher than actual generation.</p>
            </div>

            <div className="insight-divider" />

            <div className="insight-block">
              <span className="insight-label">LATEST MATCHED INTERVAL</span>
              <strong className="insight-copy">
                {loading || !latest ? "Not available" : formatDate(latest.startTime)}
              </strong>
              <p>
                {loading || !latest
                  ? "Waiting for matched observations."
                  : `Forecast ${formatMW(Number(latest.forecast))} · Actual ${formatMW(Number(latest.actual))}`}
              </p>
            </div>
          </div>
        </section>

        <section className="panel table-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent matched intervals</h2>
              <p>Forecast, actual generation and error for the selected cutoff</p>
            </div>
            <span className="subtle-pill">{points.length} intervals</span>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Target time (UTC)</th>
                  <th>Published (UTC)</th>
                  <th>Forecast</th>
                  <th>Actual</th>
                  <th>Error</th>
                  <th>Horizon</th>
                </tr>
              </thead>
              <tbody>
                {points.slice(-8).reverse().map((p, i) => (
                  <tr key={`${p.startTime}-${i}`}>
                    <td>{new Date(p.startTime).toISOString().replace("T", " ").slice(0, 16)}</td>
                    <td>{p.publishTime ? new Date(p.publishTime).toISOString().replace("T", " ").slice(0, 16) : "—"}</td>
                    <td>{formatMW(Number(p.forecast))}</td>
                    <td>{formatMW(Number(p.actual))}</td>
                    <td className={Number(p.error) > 0 ? "error-positive" : Number(p.error) < 0 ? "error-negative" : ""}>
                      {Number(p.error) > 0 ? "+" : ""}{formatMW(Number(p.error))}
                    </td>
                    <td>{Number.isFinite(Number(p.horizon_h)) ? `${Number(p.horizon_h).toFixed(1)} h` : "—"}</td>
                  </tr>
                ))}
                {!loading && points.length === 0 && (
                  <tr><td colSpan="6" className="no-rows">No matched January intervals found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="page-footer">
          <span>WindScope · Forecast decision support</span>
          <span>
            {lastUpdated ? `Data loaded ${lastUpdated.toLocaleTimeString("en-GB")}` : "Waiting for data"}
          </span>
        </footer>
      </main>
    </div>
  );
}