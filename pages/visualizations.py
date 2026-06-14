import streamlit as st
import plotly.express as px
import pandas as pd


def visualizations_page(df):

    # ====================================
    # DATA CLEANING
    # ====================================

    numeric_columns = [
        "Pre-Monsoon Level (mbgl)",
        "Post-Monsoon Level (mbgl)",
        "Annual Recharge (MCM)",
        "Extractable Resource (MCM)",
        "Total Extraction (MCM)",
        "Extraction Stage (%)",
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = df[col].astype(str).str.replace("%", "", regex=False)

            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ====================================
    # PAGE TITLE
    # ====================================

    st.title("Groundwater Visualizations")

    st.caption("Interactive groundwater analysis dashboard")

    # ====================================
    # FILTERS
    # ====================================

    st.subheader("Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_district = st.selectbox(
            "District", ["All"] + sorted(df["District"].dropna().unique())
        )

    with col2:
        selected_taluka = st.selectbox(
            "Taluka", ["All"] + sorted(df["Taluka"].dropna().unique())
        )

    with col3:
        selected_year = st.selectbox(
            "Year", ["All"] + sorted(df["Year"].dropna().unique())
        )

    filtered_df = df.copy()

    if selected_district != "All":
        filtered_df = filtered_df[filtered_df["District"] == selected_district]

    if selected_taluka != "All":
        filtered_df = filtered_df[filtered_df["Taluka"] == selected_taluka]

    if selected_year != "All":
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]

    if filtered_df.empty:

        st.warning("No data available for selected filters.")
        return

    # ====================================
    # DATA TABLE
    # ====================================

    st.subheader("Filtered Groundwater Data")

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    # ====================================
    # KPI CARDS
    # ====================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Recharge", round(filtered_df["Annual Recharge (MCM)"].mean(), 2))

    with col2:
        st.metric("Extraction", round(filtered_df["Total Extraction (MCM)"].mean(), 2))

    with col3:
        st.metric("Stage %", round(filtered_df["Extraction Stage (%)"].mean(), 2))

    with col4:
        st.metric("Records", len(filtered_df))
    st.markdown("---")

    st.success(f"""
    District : {selected_district}

    Taluka : {selected_taluka}

    Year : {selected_year}

    Records Found : {len(filtered_df)}
    """)
    st.markdown("---")

    st.subheader("Recharge Trend")

    recharge_yearly = (
        filtered_df.groupby("Year")["Annual Recharge (MCM)"].mean().reset_index()
    )

    fig_recharge = px.line(
        recharge_yearly,
        x="Year",
        y="Annual Recharge (MCM)",
        markers=True,
        title="Annual Recharge Trend",
    )

    st.plotly_chart(fig_recharge, use_container_width=True)
    st.subheader("Groundwater Level Trend")

    yearly_levels = (
        filtered_df.groupby("Year")[
            ["Pre-Monsoon Level (mbgl)", "Post-Monsoon Level (mbgl)"]
        ]
        .mean()
        .reset_index()
    )

    fig_levels = px.line(
        yearly_levels,
        x="Year",
        y=["Pre-Monsoon Level (mbgl)", "Post-Monsoon Level (mbgl)"],
        markers=True,
    )

    st.plotly_chart(fig_levels, use_container_width=True)
    # ====================================
    # PIE CHART
    # ====================================

    st.subheader("Groundwater Category Distribution")

    fig1 = px.pie(
        filtered_df,
        names="Groundwater Category",
        title="Groundwater Category Distribution",
    )

    st.plotly_chart(fig1, use_container_width=True)

    # ====================================
    # RECHARGE VS EXTRACTION
    # ====================================

    st.subheader("Recharge vs Extraction")

    district_summary = (
        filtered_df.groupby("District")[
            ["Annual Recharge (MCM)", "Total Extraction (MCM)"]
        ]
        .sum()
        .reset_index()
    )

    fig2 = px.bar(
        district_summary,
        x="District",
        y=["Annual Recharge (MCM)", "Total Extraction (MCM)"],
        barmode="group",
        title="Recharge vs Extraction",
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ====================================
    # YEAR WISE TREND
    # ====================================

    st.subheader("Year Wise Extraction Trend")

    yearly = filtered_df.groupby("Year")["Total Extraction (MCM)"].mean().reset_index()

    fig3 = px.line(
        yearly,
        x="Year",
        y="Total Extraction (MCM)",
        markers=True,
        title="Year Wise Extraction Trend",
    )

    fig3.update_layout(template="plotly_white", height=500)

    st.plotly_chart(fig3, use_container_width=True)

    # ====================================
    # TOP 10 TALUKAS
    # ====================================
    st.subheader("Top 10 Recharge Talukas")

    top_recharge = (
        filtered_df.groupby("Taluka")["Annual Recharge (MCM)"]
        .sum()
        .reset_index()
        .sort_values("Annual Recharge (MCM)", ascending=False)
        .head(10)
    )

    fig = px.bar(
        top_recharge,
        x="Taluka",
        y="Annual Recharge (MCM)",
        color="Annual Recharge (MCM)",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ====================================
    # SCATTER
    # ====================================

    st.subheader("Recharge vs Extraction Analysis")

    fig6 = px.scatter(
        filtered_df,
        x="Annual Recharge (MCM)",
        y="Total Extraction (MCM)",
        color="Groundwater Category",
        hover_data=["District", "Taluka", "Year"],
        title="Recharge vs Extraction",
    )

    st.plotly_chart(fig6, use_container_width=True)

    # ====================================
    # DISTRICT ANALYSIS
    # ====================================

    st.subheader("District Wise Extraction Stage")

    district_df = filtered_df.copy()

    fig7 = px.bar(
        district_df,
        x="Taluka",
        y="Extraction Stage (%)",
        color="Groundwater Category",
        text="Extraction Stage (%)",
        title=f"{selected_district} Groundwater Analysis",
    )

    fig7.update_layout(template="plotly_white", height=600)

    fig7.update_traces(textposition="outside")

    st.plotly_chart(fig7, use_container_width=True)
    st.subheader("District Comparison")

    compare_districts = st.multiselect(
        "Select Districts", sorted(df["District"].dropna().unique())
    )

    if len(compare_districts) > 1:

        compare_df = df[df["District"].isin(compare_districts)]

        fig_compare = px.line(
            compare_df,
            x="Year",
            y="Total Extraction (MCM)",
            color="District",
            markers=True,
            title="District Comparison",
        )

        st.plotly_chart(fig_compare, use_container_width=True)

    else:

        st.info("Please select at least 2 districts for comparison.")
