"""Analytics engine for groundwater queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from config import COL_CATEGORY, COL_DISTRICT, COL_TALUKA, COL_YEAR
from utils import format_number, metric_label


def filter_data(
    df: pd.DataFrame,
    *,
    state: str | None = None,
    district: str | None = None,
    taluka: str | None = None,
    year: int | None = None,
    category: str | None = None,
) -> pd.DataFrame:
    """Filter dataframe by common dimensions."""
    filtered = df.copy()

    if state:
        filtered = filtered[filtered["State"].str.lower() == state.lower()]
    if district:
        filtered = filtered[filtered["District"].str.lower() == district.lower()]
    if taluka:
        filtered = filtered[filtered["Taluka"].str.lower() == taluka.lower()]
    if year is not None:
        filtered = filtered[filtered["Year"] == year]
    if category:
        filtered = filtered[
            filtered["Groundwater Category"].str.contains(category, case=False, na=False)
        ]

    return filtered


def latest_record(data: pd.DataFrame) -> pd.Series | None:
    if data.empty:
        return None
    return data.sort_values("Year").iloc[-1]


def get_state_summary(df: pd.DataFrame, state: str | None = None, year: int | None = None) -> dict[str, Any]:
    """Summarize groundwater status at state level."""
    data = filter_data(df, state=state, year=year)
    if data.empty:
        return {}

    if year is None:
        data = (
            data.sort_values("Year")
            .groupby(["State", "District", "Taluka"], as_index=False)
            .tail(1)
        )

    return {
        "state": data["State"].iloc[0],
        "records": len(data),
        "districts": data["District"].nunique(),
        "talukas": data["Taluka"].nunique(),
        "avg_recharge": round(data["Annual Recharge (MCM)"].mean(), 2),
        "avg_extraction": round(data["Total Extraction (MCM)"].mean(), 2),
        "avg_stage": round(data["Extraction Stage Numeric"].mean(), 2),
        "category_counts": data["Groundwater Category"].value_counts().to_dict(),
    }


def get_district_summary(
    df: pd.DataFrame,
    district: str,
    year: int | None = None,
) -> dict[str, Any]:
    """Summarize a district."""
    data = filter_data(df, district=district, year=year)
    if data.empty:
        return {}

    if year is None:
        data = data.sort_values(["Taluka", "Year"]).groupby("Taluka", as_index=False).tail(1)

    record = latest_record(data)
    if record is None:
        return {}

    return {
        "district": record["District"],
        "state": record["State"],
        "year": int(record["Year"]),
        "talukas": data["Taluka"].nunique(),
        "avg_recharge": round(data["Annual Recharge (MCM)"].mean(), 2),
        "avg_extraction": round(data["Total Extraction (MCM)"].mean(), 2),
        "avg_stage": round(data["Extraction Stage Numeric"].mean(), 2),
        "category_counts": data["Groundwater Category"].value_counts().to_dict(),
        "latest_category": record["Groundwater Category"],
    }


def get_taluka_summary(
    df: pd.DataFrame,
    taluka: str,
    district: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Summarize a taluka."""
    data = filter_data(df, district=district, taluka=taluka, year=year)
    if data.empty:
        return {}

    record = latest_record(data)
    if record is None:
        return {}

    return {
        "taluka": record["Taluka"],
        "district": record["District"],
        "state": record["State"],
        "year": int(record["Year"]),
        "recharge": record["Annual Recharge (MCM)"],
        "extractable": record["Extractable Resource (MCM)"],
        "extraction": record["Total Extraction (MCM)"],
        "stage": record["Extraction Stage Numeric"],
        "category": record["Groundwater Category"],
        "pre_monsoon": record["Pre-Monsoon Level (mbgl)"],
        "post_monsoon": record["Post-Monsoon Level (mbgl)"],
    }


def rank_entities(
    df: pd.DataFrame,
    metric: str,
    *,
    level: str = "district",
    year: int | None = None,
    ascending: bool = False,
    top_n: int = 10,
    category: str | None = None,
) -> pd.DataFrame:
    """Rank districts or talukas by a metric."""
    data = filter_data(df, year=year, category=category)
    if data.empty:
        return pd.DataFrame()

    if year is None:
        data = (
            data.sort_values("Year")
            .groupby(["State", "District", "Taluka"], as_index=False)
            .tail(1)
        )

    group_cols = ["District"] if level == "district" else ["District", "Taluka"]
    ranked = (
        data.groupby(group_cols, as_index=False)[metric]
        .mean()
        .sort_values(metric, ascending=ascending)
        .head(top_n)
        .reset_index(drop=True)
    )
    ranked.insert(0, "Rank", ranked.index + 1)
    return ranked


def compare_entities(
    df: pd.DataFrame,
    entities: list[str],
    metric: str,
    *,
    level: str = "district",
    year: int | None = None,
) -> pd.DataFrame:
    """Compare districts or talukas on a metric across years."""
    data = df.copy()
    if level == "district":
        data = data[data["District"].isin(entities)]
        id_col = "District"
    else:
        data = data[data["Taluka"].isin(entities)]
        id_col = "Taluka"

    if year is not None:
        data = data[data["Year"] == year]

    grouped = (
        data.groupby(["Year", id_col])[metric]
        .mean()
        .reset_index()
        .sort_values(["Year", id_col])
    )
    return grouped


def trend_analysis(
    df: pd.DataFrame,
    metric: str,
    *,
    district: str | None = None,
    taluka: str | None = None,
    state: str | None = None,
) -> pd.DataFrame:
    """Return year-wise trend for a metric."""
    data = filter_data(df, state=state, district=district, taluka=taluka)
    if data.empty:
        return pd.DataFrame()

    trend = (
        data.groupby("Year")[metric]
        .mean()
        .reset_index()
        .sort_values("Year")
    )
    trend["Change"] = trend[metric].diff()
    trend["Growth Rate (%)"] = trend[metric].pct_change() * 100
    return trend


def category_distribution(df: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    """Groundwater category counts."""
    data = filter_data(df, year=year)
    if year is None:
        data = (
            data.sort_values("Year")
            .groupby(["District", "Taluka"], as_index=False)
            .tail(1)
        )
    return data["Groundwater Category"].value_counts().reset_index(name="Count")


def format_record_response(record: pd.Series, title: str) -> str:
    """Format a single record as a professional response."""
    return f"""**{title}**

- **State:** {record['State']}
- **District:** {record['District']}
- **Taluka:** {record['Taluka']}
- **Year:** {int(record['Year'])}
- **Annual Recharge:** {format_number(record['Annual Recharge (MCM)'])} MCM
- **Extractable Resource:** {format_number(record['Extractable Resource (MCM)'])} MCM
- **Total Extraction:** {format_number(record['Total Extraction (MCM)'])} MCM
- **Extraction Stage:** {format_number(record['Extraction Stage Numeric'])}%
- **Groundwater Category:** {record['Groundwater Category']}
- **Pre-Monsoon Level:** {format_number(record['Pre-Monsoon Level (mbgl)'])} mbgl
- **Post-Monsoon Level:** {format_number(record['Post-Monsoon Level (mbgl)'])} mbgl
"""


def format_ranking_response(ranked: pd.DataFrame, metric: str, level: str) -> str:
    """Format ranking table as markdown."""
    if ranked.empty:
        return "No ranking data available for the requested filters."

    lines = [f"**Top {len(ranked)} by {metric_label(metric)} ({level.title()} level)**", ""]
    for _, row in ranked.iterrows():
        if level == "district":
            label = row["District"]
        else:
            label = f"{row['Taluka']} ({row['District']})"
        lines.append(
            f"{int(row['Rank'])}. **{label}** — {format_number(row[metric])}"
        )
    return "\n".join(lines)


def format_trend_response(trend: pd.DataFrame, metric: str, entity_label: str) -> str:
    """Format trend analysis response."""
    if trend.empty:
        return f"No historical trend available for {entity_label}."

    first = trend.iloc[0]
    last = trend.iloc[-1]
    change = last[metric] - first[metric]
    direction = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"

    lines = [
        f"**Trend Analysis — {entity_label} ({metric_label(metric)})**",
        "",
        f"- **Period:** {int(first['Year'])} to {int(last['Year'])}",
        f"- **Starting value:** {format_number(first[metric])}",
        f"- **Latest value:** {format_number(last[metric])}",
        f"- **Overall change:** {format_number(change)} ({direction})",
        "",
        "**Year-wise values:**",
    ]

    for _, row in trend.iterrows():
        lines.append(f"- {int(row['Year'])}: {format_number(row[metric])}")

    return "\n".join(lines)


def get_metric_value(
    df: pd.DataFrame,
    metric: str,
    *,
    district: str | None = None,
    taluka: str | None = None,
    year: int | None = None,
) -> float | None:
    """Get a single metric value."""
    data = filter_data(df, district=district, taluka=taluka, year=year)
    record = latest_record(data)
    if record is None:
        return None
    value = record.get(metric)
    return None if pd.isna(value) else float(value)


def count_by_category(df: pd.DataFrame, category_keyword: str, year: int | None = None) -> int:
    data = filter_data(df, year=year)
    if year is None:
        data = data.sort_values("Year").groupby(["District", "Taluka"], as_index=False).tail(1)
    return len(data[data["Groundwater Category"].str.contains(category_keyword, case=False, na=False)])


@dataclass
class QueryResult:
    """Structured analytics response for dashboard pages."""

    answer: str
    data: pd.DataFrame | None = None


class DataQueryEngine:
    """High-level query interface used by app.py dashboard pages."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def state_summary(self, state: str | None = None, year: int | None = None) -> QueryResult:
        summary = get_state_summary(self.df, state=state, year=year)
        if not summary:
            label = state or "the selected state"
            return QueryResult(f"No groundwater data found for **{label}**.")

        year_label = year if year else "latest available year"
        answer = f"""
**State Summary — {summary['state']} ({year_label})**

- **Assessment units:** {summary['records']:,}
- **Districts covered:** {summary['districts']}
- **Talukas covered:** {summary['talukas']}
- **Average recharge:** {format_number(summary['avg_recharge'])} MCM
- **Average extraction:** {format_number(summary['avg_extraction'])} MCM
- **Average extraction stage:** {format_number(summary['avg_stage'])}%
- **Category distribution:** {summary['category_counts']}
"""
        return QueryResult(answer.strip())

    def district_summary(self, district: str, year: int | None = None) -> QueryResult:
        summary = get_district_summary(self.df, district, year=year)
        if not summary:
            return QueryResult(self._not_found(district))

        data = filter_data(self.df, district=district)
        if year is not None:
            data = data[data[COL_YEAR] == year]
        trend_data = (
            data.groupby(COL_YEAR, as_index=False)[
                ["Annual Recharge (MCM)", "Total Extraction (MCM)", "Extraction Stage Numeric"]
            ]
            .mean()
            .sort_values(COL_YEAR)
        )

        answer = f"""
**District Overview — {summary['district']}**

- **State:** {summary['state']}
- **Reference year:** {summary['year']}
- **Talukas covered:** {summary['talukas']}
- **Average recharge:** {format_number(summary['avg_recharge'])} MCM
- **Average extraction:** {format_number(summary['avg_extraction'])} MCM
- **Average extraction stage:** {format_number(summary['avg_stage'])}%
- **Latest category:** {summary['latest_category']}
- **Category distribution:** {summary['category_counts']}
"""
        return QueryResult(answer.strip(), trend_data if not trend_data.empty else None)

    def taluka_summary(self, taluka: str, district: str | None = None, year: int | None = None) -> QueryResult:
        summary = get_taluka_summary(self.df, taluka, district=district, year=year)
        if not summary:
            return QueryResult(self._not_found(taluka))

        data = filter_data(self.df, taluka=taluka, district=district, year=year)
        trend_data = (
            data.groupby(COL_YEAR, as_index=False)[["Extraction Stage Numeric"]]
            .mean()
            .sort_values(COL_YEAR)
        )
        answer = format_record_response(
            data.sort_values(COL_YEAR).iloc[-1],
            f"Taluka Overview — {summary['taluka']}",
        )
        return QueryResult(answer, trend_data if not trend_data.empty else None)

    def trend(
        self,
        metric_col: str,
        *,
        district: str | None = None,
        taluka: str | None = None,
        state: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> QueryResult:
        data = filter_data(self.df, state=state, district=district, taluka=taluka)
        if year_from is not None:
            data = data[data[COL_YEAR] >= year_from]
        if year_to is not None:
            data = data[data[COL_YEAR] <= year_to]

        trend = trend_analysis(
            data,
            metric_col,
            district=district,
            taluka=taluka,
            state=state,
        )
        if trend.empty:
            entity = taluka or district or state or "selected area"
            return QueryResult(f"No trend data available for **{entity}**.")

        entity_label = taluka or district or state or "Selected area"
        if taluka and district:
            entity_label = f"{taluka}, {district}"

        answer = format_trend_response(trend, metric_col, entity_label)
        return QueryResult(answer, trend)

    @staticmethod
    def _not_found(entity: str) -> str:
        return f"No groundwater data found for **{entity}** in the project dataset."
