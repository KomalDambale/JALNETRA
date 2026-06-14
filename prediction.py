"""Legacy prediction wrapper — delegates to forecasting module."""

from __future__ import annotations

import pandas as pd

from forecasting import (
    forecast_entity,
    forecast_until_2030 as _forecast_until_2030,
    get_at_risk_districts,
    predict_metric,
)
from config import MODELS_DIR
from utils import category_from_stage


def models_available() -> bool:
    """Return True when persisted XGBoost model artifacts exist."""
    return (
        (MODELS_DIR / "xgb_stage.pkl").exists()
        and (MODELS_DIR / "xgb_category.pkl").exists()
    )


def get_category(stage: float) -> str:
    return category_from_stage(stage)


def predict_groundwater(
    year: int,
    pre_monsoon: float,
    post_monsoon: float,
    recharge: float,
    extractable: float,
    extraction: float,
) -> dict[str, float | str]:
    """Rule-based single-year prediction fallback."""
    stage = round((extraction / extractable) * 100, 2) if extractable else 0.0
    return {
        "Predicted Stage": stage,
        "Predicted Category": get_category(stage),
    }


def forecast_until_2030(
    df: pd.DataFrame | None = None,
    district: str | None = None,
    taluka: str | None = None,
    *,
    pre_monsoon: float | None = None,
    post_monsoon: float | None = None,
    recharge: float | None = None,
    extractable: float | None = None,
    extraction: float | None = None,
) -> pd.DataFrame:
    """
    Forecast 2026-2030 groundwater metrics.

    Preferred usage: forecast_until_2030(df, district="Pune")
    Legacy scalar usage is still supported for backward compatibility.
    """
    if df is not None and district:
        return _forecast_until_2030(df, district, taluka)

    # Legacy fallback using simple growth assumptions
    results = []
    current_recharge = float(recharge or 0)
    current_extractable = float(extractable or 0)
    current_extraction = float(extraction or 0)
    current_pre = float(pre_monsoon or 0)
    current_post = float(post_monsoon or 0)

    for year in range(2026, 2031):
        current_recharge *= 1.01
        current_extractable *= 1.005
        current_extraction *= 1.02
        current_pre *= 1.005
        current_post *= 1.005

        prediction = predict_groundwater(
            year,
            current_pre,
            current_post,
            current_recharge,
            current_extractable,
            current_extraction,
        )
        results.append(
            {
                "Year": year,
                "Pre-Monsoon": round(current_pre, 2),
                "Post-Monsoon": round(current_post, 2),
                "Recharge": round(current_recharge, 2),
                "Extractable Resource": round(current_extractable, 2),
                "Total Extraction": round(current_extraction, 2),
                "Annual Recharge (MCM)": round(current_recharge, 2),
                "Extractable Resource (MCM)": round(current_extractable, 2),
                "Total Extraction (MCM)": round(current_extraction, 2),
                "Predicted Stage": prediction["Predicted Stage"],
                "Extraction Stage Numeric": prediction["Predicted Stage"],
                "Predicted Category": prediction["Predicted Category"],
            }
        )

    return pd.DataFrame(results)


__all__ = [
    "forecast_until_2030",
    "forecast_entity",
    "get_at_risk_districts",
    "predict_metric",
    "predict_groundwater",
    "get_category",
    "models_available",
]
