"""Query execution helpers for charts and structured responses."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import compare_entities, format_record_response, latest_record
from forecasting import forecast_entity
from visualization import comparison_chart, forecast_chart, ranking_bar, trend_line


def show_district_data(df: pd.DataFrame, district: str, year: int | None = None) -> str:
    data = df[df["District"].str.lower() == district.lower()]
    if year:
        data = data[data["Year"] == year]
    record = latest_record(data)
    if record is None:
        return f"No data found for **{district}** in the project dataset."
    return format_record_response(record, f"District Overview — {district}")


def show_graph(
    df: pd.DataFrame,
    entity: str,
    metric: str = "Total Extraction (MCM)",
    *,
    level: str = "district",
) -> None:
    if level == "district":
        data = df[df["District"].str.lower() == entity.lower()]
        title = f"{entity} — {metric} Trend"
    else:
        data = df[df["Taluka"].str.lower() == entity.lower()]
        title = f"{entity} — {metric} Trend"

    if data.empty:
        st.warning(f"No historical data available for {entity}.")
        return

    yearly = data.groupby("Year")[metric].mean().reset_index()

    yearly["Year"] = yearly["Year"].astype(str)

    fig = trend_line(yearly, x="Year", y=metric, title=title)

    fig.update_xaxes(type="category")

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"show_graph_{entity}_{metric}_{level}",
    )


def show_forecast(
    df: pd.DataFrame, district: str, taluka: str | None = None
) -> pd.DataFrame:
    forecast = forecast_entity(df, district, taluka)
    if forecast.empty:
        st.warning(f"No forecast available for {district}.")
        return forecast

    display_df = forecast.copy()

    if "Year" in display_df.columns:
        display_df["Year"] = display_df["Year"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    historical = df[df["District"].str.lower() == district.lower()]
    if taluka:
        historical = historical[historical["Taluka"].str.lower() == taluka.lower()]
    else:
        historical = historical.groupby("Year", as_index=False)[
            [
                "Extraction Stage Numeric",
                "Annual Recharge (MCM)",
                "Total Extraction (MCM)",
            ]
        ].mean()

    fig = forecast_chart(
        historical.groupby("Year")["Extraction Stage Numeric"].mean().reset_index(),
        forecast.rename(
            columns={"Extraction Stage Numeric": "Extraction Stage Numeric"}
        ),
        "Extraction Stage Numeric",
        district if not taluka else f"{taluka}, {district}",
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"forecast_{district}",
    )

    return forecast


def compare_districts(
    df: pd.DataFrame,
    district1: str,
    district2: str,
    metric: str = "Total Extraction (MCM)",
) -> str:
    comparison = compare_entities(df, [district1, district2], metric, level="district")
    if comparison.empty:
        return f"No comparable data found for **{district1}** and **{district2}**."
    comparison["Year"] = comparison["Year"].astype(str)
    fig = comparison_chart(
        comparison, x="Year", y=metric, color="District", title="District Comparison"
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"district_compare_{district1}_{district2}",
    )
    return f"Comparison chart generated for **{district1}** vs **{district2}** on {metric}."


def compare_talukas(
    df: pd.DataFrame,
    taluka1: str,
    taluka2: str,
    metric: str = "Total Extraction (MCM)",
) -> str:

    comparison = compare_entities(df, [taluka1, taluka2], metric, level="taluka")

    if comparison.empty:
        return f"No comparable data found for " f"**{taluka1}** and **{taluka2}**."
    comparison["Year"] = comparison["Year"].astype(str)
    fig = comparison_chart(
        comparison, x="Year", y=metric, color="Taluka", title="Taluka Comparison"
    )
    fig.update_xaxes(type="category")
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"taluka_compare_{taluka1}_{taluka2}",
    )

    return (
        f"Comparison chart generated for "
        f"**{taluka1}** vs **{taluka2}** "
        f"on {metric}."
    )


def show_ranking_chart(ranked: pd.DataFrame, metric: str, level: str) -> None:
    if ranked.empty:
        return

    x_col = "District" if level == "district" else "Taluka"
    fig = ranking_bar(
        ranked,
        x=x_col,
        y=metric,
        title=f"Top {len(ranked)} by {metric}",
        color=metric,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"ranking_{level}_{metric}",
    )
