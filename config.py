"""JALNETRA configuration constants."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
STYLE_PATH = PROJECT_ROOT / "style.css"

APP_NAME = "JALNETRA"
APP_TAGLINE = "AI-Driven Virtual Assistant for INGRES"

HISTORICAL_YEARS = [2021, 2022, 2023, 2024, 2025]
FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]

REQUIRED_COLUMNS = [
    "State",
    "Year",
    "District",
    "Taluka",
    "Pre-Monsoon Level (mbgl)",
    "Post-Monsoon Level (mbgl)",
    "Annual Recharge (MCM)",
    "Extractable Resource (MCM)",
    "Total Extraction (MCM)",
    "Extraction Stage (%)",
    "Groundwater Category",
]

NUMERIC_COLUMNS = [
    "Pre-Monsoon Level (mbgl)",
    "Post-Monsoon Level (mbgl)",
    "Annual Recharge (MCM)",
    "Extractable Resource (MCM)",
    "Total Extraction (MCM)",
    "Extraction Stage Numeric",
]

FORECAST_METRICS = {
    "recharge": "Annual Recharge (MCM)",
    "extractable": "Extractable Resource (MCM)",
    "extraction": "Total Extraction (MCM)",
    "stage": "Extraction Stage Numeric",
}

METRIC_ALIASES = {
    "recharge": "Annual Recharge (MCM)",
    "annual recharge": "Annual Recharge (MCM)",
    "extractable": "Extractable Resource (MCM)",
    "extractable resource": "Extractable Resource (MCM)",
    "extraction": "Total Extraction (MCM)",
    "total extraction": "Total Extraction (MCM)",
    "stage": "Extraction Stage Numeric",
    "extraction stage": "Extraction Stage Numeric",
    "pre monsoon": "Pre-Monsoon Level (mbgl)",
    "post monsoon": "Post-Monsoon Level (mbgl)",
    "category": "Groundwater Category",
}

GROUNDWATER_CATEGORIES = ["Safe", "Semi-Critical", "Critical", "Over-Exploited"]

RISK_THRESHOLDS = {
    "Low": 70,
    "Medium": 90,
    "High": 100,
}

DATA_FILE_EXTENSIONS = (".csv", ".xlsx", ".xls")
# Column Names
COL_STATE = "State"
COL_DISTRICT = "District"
COL_TALUKA = "Taluka"
COL_YEAR = "Year"
COL_CATEGORY = "Groundwater Category"
