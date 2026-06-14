"""XGBoost-based groundwater forecasting for JALNETRA."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

from config import FORECAST_METRICS, FORECAST_YEARS, HISTORICAL_YEARS
from utils import category_from_stage, risk_level_from_stage

logger = logging.getLogger(__name__)

TARGET_COLUMNS = list(FORECAST_METRICS.values())


def _entity_key(district: str, taluka: str | None = None) -> str:
    taluka_label = taluka or "DISTRICT"
    return f"{district}::{taluka_label}"


def _entity_hash(key: str) -> int:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _prepare_series(df: pd.DataFrame, district: str, taluka: str | None = None) -> pd.DataFrame:
    data = df[df["District"].str.lower() == district.lower()].copy()
    if taluka:
        data = data[data["Taluka"].str.lower() == taluka.lower()]
    else:
        numeric_cols = TARGET_COLUMNS + ["Pre-Monsoon Level (mbgl)", "Post-Monsoon Level (mbgl)"]
        data = (
            data.groupby("Year", as_index=False)[numeric_cols]
            .mean(numeric_only=True)
            .assign(District=district, Taluka="District Level")
        )

    data = data.sort_values("Year").reset_index(drop=True)
    return data


def _build_feature_rows(series: pd.DataFrame, entity_key: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    values = series.set_index("Year")

    for year in values.index:
        if year not in HISTORICAL_YEARS:
            continue

        row: dict[str, Any] = {
            "Year": int(year),
            "entity_hash": _entity_hash(entity_key),
        }

        for column in TARGET_COLUMNS:
            history = values.loc[values.index <= year, column].dropna()
            if history.empty:
                continue

            row[column] = float(history.iloc[-1])
            if len(history) >= 2:
                row[f"{column}_lag1"] = float(history.iloc[-2])
            if len(history) >= 3:
                row[f"{column}_lag2"] = float(history.iloc[-3])
            if len(history) >= 2:
                row[f"{column}_roll3"] = float(history.tail(min(3, len(history))).mean())
                prev = float(history.iloc[-2])
                current = float(history.iloc[-1])
                row[f"{column}_growth"] = ((current - prev) / prev * 100) if prev else 0.0

        rows.append(row)

    return pd.DataFrame(rows)


def _feature_columns() -> list[str]:
    columns = ["Year", "entity_hash"]
    for metric in TARGET_COLUMNS:
        columns.extend(
            [
                f"{metric}_lag1",
                f"{metric}_lag2",
                f"{metric}_roll3",
                f"{metric}_growth",
            ]
        )
    return columns


def _train_models(df: pd.DataFrame) -> tuple[dict[str, XGBRegressor], dict[str, float]]:
    """Train one XGBoost model per target metric using pooled entity data."""
    training_rows: list[pd.DataFrame] = []

    for (district, taluka), group in df.groupby(["District", "Taluka"]):
        entity_key = _entity_key(district, taluka)
        feature_rows = _build_feature_rows(group, entity_key)
        if len(feature_rows) >= 2:
            training_rows.append(feature_rows)

    if not training_rows:
        raise ValueError("Insufficient historical data to train forecasting models.")

    train_df = pd.concat(training_rows, ignore_index=True)
    feature_cols = _feature_columns()
    models: dict[str, XGBRegressor] = {}
    confidence: dict[str, float] = {}

    for target in TARGET_COLUMNS:
        model_df = train_df.dropna(subset=[target]).copy()
        if len(model_df) < 5:
            continue

        for column in feature_cols:
            if column not in model_df.columns:
                model_df[column] = 0
            model_df[column] = model_df[column].fillna(0)

        X = model_df[feature_cols]
        y = model_df[target]

        model = XGBRegressor(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            objective="reg:squarederror",
        )
        model.fit(X, y)
        preds = model.predict(X)
        mae = mean_absolute_error(y, preds)
        avg = float(y.mean()) if y.mean() else 1.0
        score = max(0.0, min(100.0, 100 - (mae / avg * 100)))
        models[target] = model
        confidence[target] = round(score, 2)

    return models, confidence


@lru_cache(maxsize=1)
def get_forecast_models(df_hash: str, df_json: str) -> tuple[dict[str, XGBRegressor], dict[str, float]]:
    """Cache trained models for a dataset snapshot."""
    df = pd.read_json(StringIO(df_json))
    return _train_models(df)


def _get_models(df: pd.DataFrame) -> tuple[dict[str, XGBRegressor], dict[str, float]]:
    snapshot = df.to_json()
    digest = hashlib.md5(snapshot.encode("utf-8")).hexdigest()
    return get_forecast_models(digest, snapshot)


def _predict_next_year(
    models: dict[str, XGBRegressor],
    history: pd.DataFrame,
    entity_key: str,
    year: int,
) -> dict[str, float]:
    values = history.set_index("Year")
    feature_cols = _feature_columns()
    row: dict[str, Any] = {"Year": year, "entity_hash": _entity_hash(entity_key)}

    for column in TARGET_COLUMNS:
        series = values[column].dropna() if column in values.columns else pd.Series(dtype=float)
        if series.empty:
            row[column] = 0.0
            continue

        row[column] = float(series.iloc[-1])
        if len(series) >= 2:
            row[f"{column}_lag1"] = float(series.iloc[-2])
        if len(series) >= 3:
            row[f"{column}_lag2"] = float(series.iloc[-3])
        row[f"{column}_roll3"] = float(series.tail(min(3, len(series))).mean())
        if len(series) >= 2:
            prev = float(series.iloc[-2])
            current = float(series.iloc[-1])
            row[f"{column}_growth"] = ((current - prev) / prev * 100) if prev else 0.0

    predictions: dict[str, float] = {}
    feature_row = pd.DataFrame([row])
    for column in feature_cols:
        if column not in feature_row.columns:
            feature_row[column] = 0
    feature_row = feature_row.fillna(0)

    for target, model in models.items():
        pred = float(model.predict(feature_row[feature_cols])[0])
        if target == "Extraction Stage Numeric":
            pred = max(0.0, pred)
        else:
            pred = max(0.0, pred)
        predictions[target] = round(pred, 2)

    extractable = predictions.get("Extractable Resource (MCM)", 0)
    extraction = predictions.get("Total Extraction (MCM)", 0)
    if extractable > 0:
        predictions["Extraction Stage Numeric"] = round((extraction / extractable) * 100, 2)

    return predictions


def forecast_entity(
    df: pd.DataFrame,
    district: str,
    taluka: str | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Forecast groundwater metrics for a district or taluka."""
    target_years = years or FORECAST_YEARS
    series = _prepare_series(df, district, taluka)
    if series.empty:
        return pd.DataFrame()

    entity_key = _entity_key(district, taluka or "District Level")
    models, confidence = _get_models(df)
    if not models:
        return _fallback_forecast(series, district, taluka, target_years)

    working = series.copy()
    rows: list[dict[str, Any]] = []

    for year in target_years:
        preds = _predict_next_year(models, working, entity_key, year)
        stage = preds.get("Extraction Stage Numeric", np.nan)
        row = {
            "Year": year,
            "District": district,
            "Taluka": taluka or "District Level",
            "Annual Recharge (MCM)": preds.get("Annual Recharge (MCM)"),
            "Extractable Resource (MCM)": preds.get("Extractable Resource (MCM)"),
            "Total Extraction (MCM)": preds.get("Total Extraction (MCM)"),
            "Extraction Stage Numeric": stage,
            "Predicted Category": category_from_stage(stage),
            "Risk Level": risk_level_from_stage(stage),
            "Confidence Score": round(np.mean(list(confidence.values())), 2) if confidence else 70.0,
        }
        rows.append(row)

        working = pd.concat(
            [
                working,
                pd.DataFrame(
                    [
                        {
                            "Year": year,
                            "District": district,
                            "Taluka": taluka or "District Level",
                            **{key: row[key] for key in TARGET_COLUMNS},
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    return pd.DataFrame(rows)


def _fallback_forecast(
    series: pd.DataFrame,
    district: str,
    taluka: str | None,
    years: list[int],
) -> pd.DataFrame:
    """Simple trend extrapolation when ML models are unavailable."""
    rows: list[dict[str, Any]] = []
    latest = series.sort_values("Year").iloc[-1]

    for index, year in enumerate(years, start=1):
        factor = 1 + (0.015 * index)
        recharge = float(latest["Annual Recharge (MCM)"]) * factor
        extractable = float(latest["Extractable Resource (MCM)"]) * (factor * 0.98)
        extraction = float(latest["Total Extraction (MCM)"]) * (factor * 1.02)
        stage = (extraction / extractable * 100) if extractable else 0

        rows.append(
            {
                "Year": year,
                "District": district,
                "Taluka": taluka or "District Level",
                "Annual Recharge (MCM)": round(recharge, 2),
                "Extractable Resource (MCM)": round(extractable, 2),
                "Total Extraction (MCM)": round(extraction, 2),
                "Extraction Stage Numeric": round(stage, 2),
                "Predicted Category": category_from_stage(stage),
                "Risk Level": risk_level_from_stage(stage),
                "Confidence Score": 55.0,
            }
        )

    return pd.DataFrame(rows)


def predict_metric(
    df: pd.DataFrame,
    district: str,
    metric: str,
    target_year: int,
    taluka: str | None = None,
) -> dict[str, Any] | None:
    """Predict a single metric for a given year."""
    forecast = forecast_entity(df, district, taluka)
    if forecast.empty:
        return None

    match = forecast[forecast["Year"] == target_year]
    if match.empty:
        return None

    row = match.iloc[0]
    metric_map = {
        "recharge": "Annual Recharge (MCM)",
        "extractable": "Extractable Resource (MCM)",
        "extraction": "Total Extraction (MCM)",
        "stage": "Extraction Stage Numeric",
    }
    column = metric_map.get(metric, metric)
    return {
        "district": district,
        "taluka": taluka or "District Level",
        "year": target_year,
        "metric": column,
        "value": row.get(column),
        "category": row.get("Predicted Category"),
        "risk_level": row.get("Risk Level"),
        "confidence": row.get("Confidence Score"),
    }


def get_at_risk_districts(
    df: pd.DataFrame,
    target_year: int = 2030,
    min_risk: str = "High",
) -> pd.DataFrame:
    """Identify districts with elevated future groundwater risk."""
    risk_order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3, "Unknown": -1}
    min_level = risk_order.get(min_risk, 2)
    rows: list[dict[str, Any]] = []

    for district in sorted(df["District"].dropna().unique()):
        forecast = forecast_entity(df, district)
        if forecast.empty:
            continue
        match = forecast[forecast["Year"] == target_year]
        if match.empty:
            continue
        row = match.iloc[0]
        level = row["Risk Level"]
        if risk_order.get(level, -1) >= min_level:
            rows.append(
                {
                    "District": district,
                    "Predicted Stage 2030": row["Extraction Stage Numeric"],
                    "Predicted Category": row["Predicted Category"],
                    "Risk Level": level,
                    "Confidence Score": row["Confidence Score"],
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("Predicted Stage 2030", ascending=False).reset_index(drop=True)


def forecast_until_2030(
    df: pd.DataFrame,
    district: str,
    taluka: str | None = None,
) -> pd.DataFrame:
    """Backward-compatible wrapper used by legacy imports."""
    return forecast_entity(df, district, taluka)


def format_forecast_response(forecast: pd.DataFrame, entity_label: str) -> str:
    if forecast.empty:
        return f"No forecast could be generated for {entity_label}."

    final = forecast.iloc[-1]
    lines = [
        f"**5-Year Groundwater Forecast — {entity_label}**",
        "",
        "Based on 2021–2025 historical data using XGBoost with lag, rolling average, and growth features.",
        "",
        f"- **2030 Predicted Stage:** {final['Extraction Stage Numeric']}%",
        f"- **2030 Predicted Category:** {final['Predicted Category']}",
        f"- **2030 Risk Level:** {final['Risk Level']}",
        f"- **Model Confidence:** {final['Confidence Score']}%",
        "",
        "**Year-wise projection:**",
    ]

    for _, row in forecast.iterrows():
        lines.append(
            f"- **{int(row['Year'])}:** Stage {row['Extraction Stage Numeric']}%, "
            f"Recharge {row['Annual Recharge (MCM)']} MCM, "
            f"Extraction {row['Total Extraction (MCM)']} MCM"
        )

    return "\n".join(lines)


def forecast_district(
    df: pd.DataFrame,
    district: str,
    *,
    horizon: int = 5,
    taluka: str | None = None,
) -> pd.DataFrame:
    """Forecast groundwater metrics for a district over a configurable horizon."""
    target_years = FORECAST_YEARS[: max(1, min(horizon, len(FORECAST_YEARS)))]
    forecast = forecast_entity(df, district, taluka, years=target_years)
    if forecast.empty:
        return forecast

    forecast = forecast.copy()
    forecast["Predicted Stage"] = forecast["Extraction Stage Numeric"]
    return forecast
