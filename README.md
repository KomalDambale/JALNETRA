# JALNETRA — AI Groundwater Analysis Platform

JALNETRA is an AI-driven virtual assistant for INGRES groundwater assessment data. It provides interactive dashboards, data-grounded natural language queries, and XGBoost-based forecasts for Maharashtra groundwater resources (2021–2025 historical, 2026–2030 projected).

## Features

- **Groundwater Overview** — KPI cards, category distribution, statewide trends
- **District & Taluka Analysis** — Drill-down charts and tables
- **Trend Analysis** — Year-wise comparisons and rankings
- **Forecast Center** — XGBoost predictions with confidence scores and risk levels
- **AI Chatbot** — Natural-language queries answered only from project data/models
- **Data Explorer** — Filter, inspect, and download assessment records

## Quick Start

```bash
# Clone or open the project
cd WATER

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Project Structure

```
WATER/
├── app.py              # Streamlit dashboard entry point
├── chatbot.py          # Data-grounded AI chatbot
├── data_loader.py      # CSV/Excel loading and cleaning
├── analytics.py        # Rankings, trends, comparisons
├── forecasting.py      # XGBoost forecasting engine
├── prediction.py       # Legacy prediction wrapper
├── visualization.py    # Plotly chart helpers
├── nlp_engine.py       # Intent detection & NLP
├── query_engine.py     # Chart/query execution
├── config.py           # Constants and paths
├── utils.py            # Shared helpers
├── data/               # Groundwater datasets
├── pages/              # Streamlit sub-pages
└── requirements.txt
```

## Data

Place groundwater CSV or Excel files in the `data/` folder. The loader auto-discovers files, removes duplicates, parses numeric ranges (e.g. `3.5 - 6.2`), and validates required columns.

Required columns:
- State, Year, District, Taluka
- Pre-Monsoon Level (mbgl), Post-Monsoon Level (mbgl)
- Annual Recharge (MCM), Extractable Resource (MCM), Total Extraction (MCM)
- Extraction Stage (%), Groundwater Category

## Chatbot Examples

- `Show Pune recharge in 2024`
- `Top 10 districts by extraction stage`
- `Compare Nashik vs Pune extraction`
- `Predict groundwater extraction stage for Pune in 2030`
- `Forecast recharge for Nashik in 2028`
- `Which districts are at future groundwater risk?`
- `Show next 5-year trend for Ahmednagar`

## Deployment

### Streamlit Cloud

1. Push the repo to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Set main file: `app.py`
4. Add secrets in the dashboard if using email OTP (`.streamlit/secrets.toml`)

### Render

Uses `render.yaml` — connect repo and deploy as a Web Service.

### Railway

Uses `Procfile` — deploy with:

```bash
railway up
```

## Email OTP (Optional)

Create `.streamlit/secrets.toml`:

```toml
EMAIL_ADDRESS = "your@gmail.com"
EMAIL_PASSWORD = "your-app-password"
```

## Requirements

- Python 3.10+
- See `requirements.txt` for full dependency list

## License

Built for INGRES groundwater resource management.
