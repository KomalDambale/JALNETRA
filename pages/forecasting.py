"""Groundwater forecasting dashboard page."""

from __future__ import annotations

import streamlit as st

from forecasting import forecast_entity, get_at_risk_districts
from utils import format_number
from visualization import multi_metric_forecast_chart, recharge_extraction_bar, risk_heatmap, trend_line


def forecasting_page(df) -> None:
    st.title("Forecast Center")
    st.caption("XGBoost-powered 2026–2030 groundwater projections using 2021–2025 historical data")

    districts = sorted(df["District"].dropna().unique())
    col1, col2 = st.columns(2)
    with col1:
        district = st.selectbox("District", districts, key="forecast_district")
    with col2:
        talukas = sorted(df[df["District"] == district]["Taluka"].dropna().unique())
        taluka = st.selectbox("Taluka (optional)", ["District Level"] + talukas, key="forecast_taluka")

    selected_taluka = None if taluka == "District Level" else taluka
    district_data = df[df["District"] == district]
    if selected_taluka:
        district_data = district_data[district_data["Taluka"] == selected_taluka]

    years = sorted(district_data["Year"].dropna().unique())
    selected_year = st.selectbox("Base Year", years, index=len(years) - 1, key="forecast_year")

    latest_rows = district_data[district_data["Year"] == selected_year]
    if latest_rows.empty:
        st.warning("No data available for selected filters.")
        return

    latest = latest_rows.iloc[0]
    st.subheader("Current Groundwater Status")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("District", district)
    c2.metric("Base Year", int(selected_year))
    c3.metric("Recharge (MCM)", format_number(latest["Annual Recharge (MCM)"]))
    c4.metric("Extraction (MCM)", format_number(latest["Total Extraction (MCM)"]))
    c5.metric("Stage %", format_number(latest["Extraction Stage Numeric"]))

    history = district_data.groupby("Year")["Extraction Stage Numeric"].mean().reset_index()
    st.plotly_chart(
        trend_line(history, x="Year", y="Extraction Stage Numeric", title=f"{district} Historical Extraction Stage"),
        use_container_width=True,
    )

    if st.button("Generate Forecast", type="primary", key="generate_forecast"):
        forecast = forecast_entity(df, district, selected_taluka)
        if forecast.empty:
            st.error("Forecast generation failed.")
            return

        final = forecast.iloc[-1]
        st.success("Forecast generated successfully")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("2030 Stage %", format_number(final["Extraction Stage Numeric"]))
        k2.metric("2030 Category", final["Predicted Category"])
        k3.metric("Risk Level", final["Risk Level"])
        k4.metric("Confidence", f"{final['Confidence Score']}%")

        entity = f"{selected_taluka}, {district}" if selected_taluka else district
        st.plotly_chart(multi_metric_forecast_chart(forecast, entity), use_container_width=True)
        st.plotly_chart(recharge_extraction_bar(forecast, x="Year", title=f"{entity} Recharge vs Extraction"), use_container_width=True)
        st.dataframe(forecast, use_container_width=True, hide_index=True)

        stage = float(final["Extraction Stage Numeric"])
        if stage < 70:
            st.success("Groundwater is projected to remain in the Safe zone through 2030.")
        elif stage < 90:
            st.warning("Groundwater is projected to move toward Semi-Critical conditions.")
        else:
            st.error("Groundwater may reach Critical or Over-Exploited levels by 2030.")

    st.markdown("---")
    st.subheader("Districts at Future Risk (2030)")
    risk_df = get_at_risk_districts(df, target_year=2030, min_risk="High")
    if risk_df.empty:
        st.info("No districts projected at High or Critical risk in 2030.")
    else:
        st.plotly_chart(risk_heatmap(risk_df.head(20)), use_container_width=True)
        st.dataframe(risk_df, use_container_width=True, hide_index=True)
