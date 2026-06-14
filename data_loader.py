"""Data loading and cleaning for JALNETRA."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import DATA_DIR, DATA_FILE_EXTENSIONS, NUMERIC_COLUMNS, REQUIRED_COLUMNS
from utils import normalize_name, parse_numeric_value

logger = logging.getLogger(__name__)


def _read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {path}")


def discover_data_files(data_dir: Path | None = None) -> list[Path]:
    """Find CSV and Excel files in the data directory."""
    directory = data_dir or DATA_DIR
    if not directory.exists():
        return []

    files: list[Path] = []
    for extension in DATA_FILE_EXTENSIONS:
        files.extend(directory.glob(f"*{extension}"))

    return sorted(set(files))


def validate_columns(df: pd.DataFrame) -> None:
    """Ensure required columns exist."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean, deduplicate, and validate groundwater data."""
    cleaned = df.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]

    validate_columns(cleaned)

    cleaned["State"] = cleaned["State"].apply(lambda value: normalize_name(value, "Unknown"))
    cleaned["District"] = cleaned["District"].apply(lambda value: normalize_name(value))
    cleaned["Taluka"] = cleaned["Taluka"].fillna("District Level").apply(
        lambda value: normalize_name(value, "District Level")
    )
    cleaned["Year"] = pd.to_numeric(cleaned["Year"], errors="coerce").astype("Int64")
    cleaned["Groundwater Category"] = (
        cleaned["Groundwater Category"].astype(str).str.strip().replace({"nan": "Unknown"})
    )

    numeric_source_columns = [
        "Pre-Monsoon Level (mbgl)",
        "Post-Monsoon Level (mbgl)",
        "Annual Recharge (MCM)",
        "Extractable Resource (MCM)",
        "Total Extraction (MCM)",
        "Extraction Stage (%)",
    ]

    for column in numeric_source_columns:
        cleaned[column] = cleaned[column].apply(parse_numeric_value)

    cleaned["Extraction Stage Numeric"] = cleaned["Extraction Stage (%)"]

    missing_stage = cleaned["Extraction Stage Numeric"].isna()
    extractable = cleaned["Extractable Resource (MCM)"]
    extraction = cleaned["Total Extraction (MCM)"]
    cleaned.loc[missing_stage, "Extraction Stage Numeric"] = (
        (extraction / extractable.replace(0, pd.NA)) * 100
    ).round(2)

    cleaned = cleaned.dropna(subset=["District", "Year"])
    cleaned = cleaned.drop_duplicates(
        subset=["State", "Year", "District", "Taluka"],
        keep="last",
    )

    for column in NUMERIC_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.sort_values(["State", "District", "Taluka", "Year"]).reset_index(drop=True)
    return cleaned


def load_all_data(data_dir: Path | None = None) -> pd.DataFrame:
    """Auto-load and merge all CSV/Excel groundwater files."""
    files = discover_data_files(data_dir)
    if not files:
        raise FileNotFoundError(
            f"No groundwater data files found in {(data_dir or DATA_DIR).resolve()}"
        )

    frames: list[pd.DataFrame] = []
    for path in files:
        logger.info("Loading data file: %s", path.name)
        raw = _read_file(path)
        frames.append(clean_dataframe(raw))

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["State", "Year", "District", "Taluka"],
        keep="last",
    )
    combined = combined.sort_values(["State", "District", "Taluka", "Year"]).reset_index(drop=True)

    logger.info(
        "Loaded %s records across %s districts and %s years",
        len(combined),
        combined["District"].nunique(),
        combined["Year"].nunique(),
    )
    return combined


def load_master_dataframe(data_dir: Path | None = None) -> pd.DataFrame:
    """Load and cache the combined groundwater dataset for the app."""
    return load_all_data(data_dir)


def get_data_summary(df: pd.DataFrame) -> dict[str, int | list[int]]:
    """Return high-level dataset summary."""
    return {
        "records": len(df),
        "states": df["State"].nunique(),
        "districts": df["District"].nunique(),
        "talukas": df["Taluka"].nunique(),
        "years": sorted(df["Year"].dropna().astype(int).unique().tolist()),
        "categories": df["Groundwater Category"].nunique(),
    }
