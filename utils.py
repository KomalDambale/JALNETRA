"""Shared utility helpers for JALNETRA."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from config import GROUNDWATER_CATEGORIES, RISK_THRESHOLDS


def parse_numeric_value(value: Any) -> float | None:
    """Parse numeric values including ranges like '3.5 - 6.2'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip().replace("%", "")
    if not text or text.lower() in {"nan", "none", "-", "na"}:
        return None

    range_match = re.match(
        r"^\s*(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)\s*$",
        text,
    )
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return round((low + high) / 2, 4)

    cleaned = re.sub(r"[^\d.\-]", "", text)
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_name(value: Any, fallback: str = "") -> str:
    """Normalize district/taluka/state names."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text.title() if text else fallback


def category_from_stage(stage: float | None) -> str:
    """Map extraction stage percentage to groundwater category."""
    if stage is None or pd.isna(stage):
        return "Unknown"

    stage = float(stage)
    if stage < 70:
        return "Safe"
    if stage < 90:
        return "Semi-Critical"
    if stage < 100:
        return "Critical"
    return "Over-Exploited"


def risk_level_from_stage(stage: float | None) -> str:
    """Map extraction stage to future risk level."""
    if stage is None or pd.isna(stage):
        return "Unknown"

    stage = float(stage)
    if stage < RISK_THRESHOLDS["Low"]:
        return "Low"
    if stage < RISK_THRESHOLDS["Medium"]:
        return "Medium"
    if stage < RISK_THRESHOLDS["High"]:
        return "High"
    return "Critical"


def format_number(value: Any, decimals: int = 2, suffix: str = "") -> str:
    """Format numeric values for chat responses."""
    parsed = parse_numeric_value(value)
    if parsed is None:
        return "N/A"
    if suffix:
        return f"{parsed:.{decimals}f} {suffix}".strip()
    return f"{parsed:.{decimals}f}"


def metric_label(column: str) -> str:
    """Human-readable metric label."""
    mapping = {
        "Annual Recharge (MCM)": "Annual Recharge",
        "Extractable Resource (MCM)": "Extractable Resource",
        "Total Extraction (MCM)": "Total Extraction",
        "Extraction Stage Numeric": "Extraction Stage",
        "Pre-Monsoon Level (mbgl)": "Pre-Monsoon Level",
        "Post-Monsoon Level (mbgl)": "Post-Monsoon Level",
        "Groundwater Category": "Groundwater Category",
    }
    return mapping.get(column, column)


def resolve_metric(query: str) -> str | None:
    """Resolve a metric column from natural language."""
    from config import METRIC_ALIASES

    query = query.lower()
    for alias, column in sorted(METRIC_ALIASES.items(), key=lambda item: -len(item[0])):
        if alias in query:
            return column
    return None


def is_valid_category(value: str) -> bool:
    return value in GROUNDWATER_CATEGORIES


def copy_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a defensive copy of a dataframe."""
    return df.copy()


def load_css(path: str) -> str:
    """Load stylesheet content from disk."""
    css_path = Path(path)
    if not css_path.exists():
        return ""
    return css_path.read_text(encoding="utf-8")
