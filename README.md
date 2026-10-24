# Gridbricks Wind Forecast Dashboard

A data-driven dashboard for analyzing wind generation forecasts against actual generation in Great Britain, using data from the Elexon BMRS API.

## Overview

Wind generation forecasts are important for electricity market planning and balancing. This project provides a dashboard to compare forecast wind generation with actual generation and explore forecast performance at different lead times.

The application combines a Python FastAPI backend with a React frontend to process generation data and present analysis through an interactive dashboard.

## Features

- **Forecast vs Actual:** Compare predicted wind generation with observed generation.
- **Forecast Error Analysis:** Evaluate differences between forecast and actual values.
- **Performance Metrics:** Display summary statistics for forecast performance.
- **Forecast Horizon Analysis:** Explore how forecast lead time relates to accuracy.
- **API Endpoints:** Access processed data and analysis through FastAPI.
- **Data Files:** Use CSV datasets for wind forecasts and actual generation.

## Technology Stack

- **Frontend:** React, JavaScript, Vite, CSS
- **Backend:** Python, FastAPI
- **Data Processing:** Pandas, NumPy
- **Data Source:** Elexon BMRS API
- **Testing:** Pytest

## Project Structure

```text
wind-forecast/
├── backend/
│   ├── app/
│   │   ├── analysis.py
│   │   ├── config.py
│   │   ├── ingest.py
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── data/
│   ├── actuals.csv
│   └── forecasts.csv
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Getting Started

### Prerequisites

- Python installed
- Node.js and npm installed
- Git installed

### 1. Clone the repository

```bash
git clone https://github.com/Adroy-Nazareth/gridbricks-wind-forecast.git
cd gridbricks-wind-forecast
```

### 2. Start the backend

Open a terminal in the project root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and start the API:

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The backend API will be available at:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### 3. Start the frontend

Open a second terminal in the project root:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually:

`http://localhost:5173`

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/health` | Check backend health |
| `/api/forecast` | Retrieve forecast and actual generation data |
| `/api/metrics` | Retrieve forecast performance metrics |
| `/api/horizon` | Analyze performance by forecast horizon |
| `/api/buy` | Retrieve the application's buy-related analysis |

For the available parameters and response formats, visit `/docs` while the backend is running.

## Data

The project contains two CSV datasets:

- `data/forecasts.csv` — wind generation forecasts and publication timestamps.
- `data/actuals.csv` — observed wind generation values.

The backend processes these datasets to align forecasts with actual generation and analyze forecast performance.

## Testing

From the project root, run:

```bash
cd backend
pytest
```

## Future Improvements

- Add more detailed forecast error visualizations.
- Compare forecast accuracy across different lead times.
- Improve data validation and missing-value handling.
- Add automated data refresh and deployment.

## Author

**Adroy Nazareth**

B.Tech — Artificial Intelligence and Machine Learning

GitHub: [Adroy-Nazareth](https://github.com/Adroy-Nazareth)
