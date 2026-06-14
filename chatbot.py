"""Data-grounded AI chatbot for JALNETRA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import (
    category_distribution,
    count_by_category,
    filter_data,
    format_ranking_response,
    format_record_response,
    format_trend_response,
    get_district_summary,
    get_state_summary,
    latest_record,
    rank_entities,
    trend_analysis,
)
from analytics import compare_entities
from forecasting import (
    format_forecast_response,
    forecast_entity,
    get_at_risk_districts,
    predict_metric,
)
from nlp_engine import (
    detect_category_filter,
    detect_intent,
    detect_metric,
    extract_district,
    extract_districts_for_compare,
    extract_state,
    extract_taluka,
    extract_top_n,
    extract_year,
    is_ascending_rank,
    is_count_query,
    preprocess_query,
)
from query_engine import compare_districts, show_graph, show_ranking_chart
from query_engine import compare_talukas
from utils import format_number, metric_label
from visualization import category_pie, multi_metric_forecast_chart, risk_heatmap


@dataclass
class ChatMemory:
    """Short-term conversation memory for follow-up queries."""

    last_district: str | None = None
    last_taluka: str | None = None
    last_year: int | None = None
    last_intent: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)

    def remember(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self.history = self.history[-12:]

    def update_context(
        self,
        *,
        district: str | None = None,
        taluka: str | None = None,
        year: int | None = None,
        intent: str | None = None,
    ) -> None:
        if district:
            self.last_district = district
        if taluka:
            self.last_taluka = taluka
        if year:
            self.last_year = year
        if intent:
            self.last_intent = intent


class JalnetraChatbot:
    """Groundwater chatbot that answers only from project data and models."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _memory(self) -> ChatMemory:
        if "chat_memory" not in st.session_state:
            st.session_state.chat_memory = ChatMemory()
        return st.session_state.chat_memory

    def _resolve_district(self, query: str) -> str | None:
        memory = self._memory()
        district = extract_district(query, self.df)
        return district

    def _resolve_taluka(self, query: str) -> str | None:
        memory = self._memory()
        return extract_taluka(query, self.df)

    def _resolve_year(self, query: str) -> int | None:
        memory = self._memory()
        return extract_year(query) or memory.last_year

    def _not_found(self, entity: str) -> str:
        return (
            f"I couldn't find **{entity}** in the JALNETRA groundwater dataset. "
            "Please check the district or taluka spelling."
        )

    def _handle_help(self) -> str:
        return """
**JALNETRA can help with:**

- District / taluka / state / year-wise groundwater data
- Rankings and comparisons
- Historical trend analysis (2021–2025)
- Future forecasts (2026–2030) with risk levels
- Automatic charts when useful

**Examples:**
- Show Pune recharge in 2024
- Top 10 districts by extraction stage
- Compare Nashik vs Pune extraction trend
- Predict groundwater extraction stage for Pune in 2030
- Forecast recharge for Nashik in 2028
- Which districts are at future groundwater risk?
- Show next 5-year trend for Ahmednagar
"""

    def _handle_state(self, query: str) -> str:
        state = extract_state(query, self.df) or self.df["State"].iloc[0]
        year = self._resolve_year(query)
        summary = get_state_summary(self.df, state=state, year=year)
        if not summary:
            return self._not_found(state)

        self._memory().update_context(year=year, intent="state")
        year_label = year if year else "latest available year"
        return f"""
**State Summary — {summary['state']} ({year_label})**

- **Assessment units:** {summary['records']}
- **Districts covered:** {summary['districts']}
- **Talukas covered:** {summary['talukas']}
- **Average recharge:** {summary['avg_recharge']} MCM
- **Average extraction:** {summary['avg_extraction']} MCM
- **Average extraction stage:** {summary['avg_stage']}%
- **Category distribution:** {summary['category_counts']}
"""

    def _handle_rank(self, query: str) -> str:
        metric = detect_metric(query) or "Extraction Stage Numeric"
        year = self._resolve_year(query)
        top_n = extract_top_n(query)
        ascending = is_ascending_rank(query)
        level = "taluka" if "taluka" in preprocess_query(query) else "district"
        category = detect_category_filter(query)

        ranked = rank_entities(
            self.df,
            metric,
            level=level,
            year=year,
            ascending=ascending,
            top_n=top_n,
            category=category,
        )
        if ranked.empty:
            return "No ranking results found for your query in the dataset."

        show_ranking_chart(ranked, metric, level)
        self._memory().update_context(year=year, intent="rank")
        return format_ranking_response(ranked, metric, level)

    def _handle_compare(self, query: str) -> str:
        metric = detect_metric(query) or "Total Extraction (MCM)"

        # District comparison
        districts = extract_districts_for_compare(query, self.df)

        if len(districts) >= 2:
            response = compare_districts(self.df, districts[0], districts[1], metric)

            self._memory().update_context(district=districts[0], intent="compare")

            return response

        # Taluka comparison
        talukas = []

        for taluka in self.df["Taluka"].dropna().unique():
            if str(taluka).lower() in query.lower():
                talukas.append(taluka)

        if len(talukas) >= 2:
            return compare_talukas(self.df, talukas[0], talukas[1], metric)

        return "Please mention at least two districts or " "two talukas to compare."

    def _handle_trend(self, query: str) -> str:
        metric = detect_metric(query) or "Extraction Stage Numeric"
        district = self._resolve_district(query)
        taluka = self._resolve_taluka(query)
        state = extract_state(query, self.df)

        if not any([district, taluka, state]):
            return "Please specify a district, taluka, or state for trend analysis."

        trend = trend_analysis(
            self.df,
            metric,
            district=district,
            taluka=taluka,
            state=state,
        )
        if trend.empty:
            return "No trend data available for the requested filters."

        entity_label = taluka or district or state or "Selected area"
        if taluka and district:
            entity_label = f"{taluka}, {district}"
        elif district:
            entity_label = district
        trend["Year"] = trend["Year"].astype(str)
        fig = px.line(
            trend,
            x="Year",
            y=metric,
            markers=True,
            title=f"{entity_label} — {metric_label(metric)} Trend",
        )
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, use_container_width=True)
        self._memory().update_context(district=district, taluka=taluka, intent="trend")
        return format_trend_response(trend, metric, entity_label)

    def _handle_forecast(self, query: str) -> str:
        district = self._resolve_district(query)
        taluka = self._resolve_taluka(query)
        target_year = extract_year(query)
        metric = detect_metric(query)

        if "risk" in preprocess_query(query) or "which districts" in preprocess_query(
            query
        ):
            return self._handle_risk(query)

        if not district and not taluka:
            return "Please specify a district or taluka for forecasting, e.g. *Forecast recharge for Nashik in 2028*."

        if metric and target_year and district:
            metric_key = {
                "Annual Recharge (MCM)": "recharge",
                "Extractable Resource (MCM)": "extractable",
                "Total Extraction (MCM)": "extraction",
                "Extraction Stage Numeric": "stage",
            }.get(metric, "stage")
            result = predict_metric(self.df, district, metric_key, target_year, taluka)
            if not result:
                return self._not_found(district)
            self._memory().update_context(
                district=district, taluka=taluka, intent="forecast"
            )
            return f"""
**Forecast Result — {district}{f' ({taluka})' if taluka else ''}**

- **Target year:** {target_year}
- **Metric:** {metric_label(result['metric'])}
- **Predicted value:** {format_number(result['value'])}
- **Predicted category:** {result['category']}
- **Risk level:** {result['risk_level']}
- **Confidence score:** {result['confidence']}%
"""

        forecast = (
            forecast_entity(self.df, district, taluka) if district else pd.DataFrame()
        )
        if forecast.empty:
            return self._not_found(district or taluka or "requested area")

        fig = multi_metric_forecast_chart(
            forecast, district if not taluka else f"{taluka}, {district}"
        )
        st.plotly_chart(fig, use_container_width=True)
        display_df = forecast.copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        self._memory().update_context(
            district=district, taluka=taluka, intent="forecast"
        )
        label = f"{taluka}, {district}" if taluka else district
        return format_forecast_response(forecast, label)

    def _handle_risk(self, query: str) -> str:
        target_year = extract_year(query) or 2030
        risk_df = get_at_risk_districts(
            self.df, target_year=target_year, min_risk="High"
        )
        if risk_df.empty:
            return f"No districts are projected at High or Critical risk in **{target_year}** based on current models."

        fig = risk_heatmap(risk_df.head(15))
        st.plotly_chart(fig, use_container_width=True)
        display_df = risk_df.copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(int).astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        lines = [
            f"**Districts at Future Groundwater Risk ({target_year})**",
            "",
            "The following districts are projected to reach High or Critical extraction stages:",
            "",
        ]
        for _, row in risk_df.head(10).iterrows():
            lines.append(
                f"- **{row['District']}** — Stage {row['Predicted Stage 2030']}%, "
                f"{row['Predicted Category']} ({row['Risk Level']} risk)"
            )
        return "\n".join(lines)

    def _handle_graph(self, query: str) -> str:
        metric = detect_metric(query) or "Total Extraction (MCM)"
        district = self._resolve_district(query)
        taluka = self._resolve_taluka(query)

        if taluka:
            show_graph(self.df, taluka, metric, level="taluka")
            self._memory().update_context(
                district=district, taluka=taluka, intent="graph"
            )
            return f"Generated a trend chart for **{taluka}** ({metric_label(metric)})."

        if district:
            show_graph(self.df, district, metric, level="district")
            self._memory().update_context(district=district, intent="graph")
            return (
                f"Generated a trend chart for **{district}** ({metric_label(metric)})."
            )

        return "Please specify a district or taluka to generate a chart."

    def _handle_category_distribution(self, query: str) -> str:
        year = self._resolve_year(query)
        distribution = category_distribution(self.df, year=year)
        if distribution.empty:
            return "Category distribution is not available for the requested filters."

        fig = category_pie(distribution, title="Groundwater Category Distribution")
        st.plotly_chart(fig, use_container_width=True)
        return f"Groundwater category distribution{' for ' + str(year) if year else ''} displayed."

    def _handle_counts(self, query: str) -> str:
        category = detect_category_filter(query) or "Critical"
        year = self._resolve_year(query)
        count = count_by_category(self.df, category.replace("-", ""), year=year)
        return f"Total **{category}** assessment units{' in ' + str(year) if year else ''}: **{count}**"

    def _handle_correlation(self) -> str:
        corr = (
            self.df[["Annual Recharge (MCM)", "Extraction Stage Numeric"]]
            .corr()
            .iloc[0, 1]
        )

        return (
            f"Correlation between Annual Recharge and " f"Extraction Stage = {corr:.3f}"
        )

    def _handle_entity_lookup(self, query: str, intent: str) -> str:
        district = self._resolve_district(query)
        taluka = self._resolve_taluka(query)
        year = self._resolve_year(query)

        if taluka:
            data = filter_data(self.df, taluka=taluka, district=district, year=year)
            record = latest_record(data)
            if record is None:
                return self._not_found(taluka)
            self._memory().update_context(
                district=record["District"],
                taluka=taluka,
                year=int(record["Year"]),
                intent=intent,
            )

            if intent == "data":
                display_df = data.copy()

                if "Year" in display_df.columns:
                    display_df["Year"] = display_df["Year"].astype(int).astype(str)

                st.dataframe(display_df, use_container_width=True, hide_index=True)
                return (
                    f"Showing dataset records for **{taluka}** ({record['District']})."
                )

            if intent in {
                "recharge",
                "extractable",
                "extraction",
                "stage",
                "category",
                "pre_monsoon",
                "post_monsoon",
            }:
                mapping = {
                    "recharge": ("Annual Recharge (MCM)", "MCM"),
                    "extractable": ("Extractable Resource (MCM)", "MCM"),
                    "extraction": ("Total Extraction (MCM)", "MCM"),
                    "stage": ("Extraction Stage Numeric", "%"),
                    "category": ("Groundwater Category", ""),
                    "pre_monsoon": ("Pre-Monsoon Level (mbgl)", "mbgl"),
                    "post_monsoon": ("Post-Monsoon Level (mbgl)", "mbgl"),
                }
                column, suffix = mapping[intent]
                value = record[column]
                if intent == "category":
                    return f"**{taluka}** ({record['District']}, {int(record['Year'])}) groundwater category: **{value}**"
                return (
                    f"**{taluka}** ({record['District']}, {int(record['Year'])}) "
                    f"{metric_label(column)}: **{format_number(value)}{suffix}**"
                )

            return format_record_response(record, f"Taluka Overview — {taluka}")

        if district:
            data = filter_data(self.df, district=district, year=year)
            record = latest_record(data)
            if record is None:
                return self._not_found(district)
            self._memory().update_context(
                district=district, year=int(record["Year"]), intent=intent
            )

            if intent == "data":
                display_df = data.copy()

                if "Year" in display_df.columns:
                    display_df["Year"] = display_df["Year"].astype(int).astype(str)

                st.dataframe(display_df, use_container_width=True, hide_index=True)
                return f"Showing dataset records for **{district}**."

            if intent in {
                "recharge",
                "extractable",
                "extraction",
                "stage",
                "category",
                "pre_monsoon",
                "post_monsoon",
            }:
                mapping = {
                    "recharge": ("Annual Recharge (MCM)", "MCM"),
                    "extractable": ("Extractable Resource (MCM)", "MCM"),
                    "extraction": ("Total Extraction (MCM)", "MCM"),
                    "stage": ("Extraction Stage Numeric", "%"),
                    "category": ("Groundwater Category", ""),
                    "pre_monsoon": ("Pre-Monsoon Level (mbgl)", "mbgl"),
                    "post_monsoon": ("Post-Monsoon Level (mbgl)", "mbgl"),
                }
                column, suffix = mapping[intent]
                value = record[column]
                if intent == "category":
                    return f"**{district}** ({int(record['Year'])}) groundwater category: **{value}**"
                return (
                    f"**{district}** ({int(record['Year'])}) "
                    f"{metric_label(column)}: **{format_number(value)}{suffix}**"
                )

            summary = get_district_summary(self.df, district, year=year)
            return f"""
**District Overview — {district}**

- **State:** {summary.get('state', record['State'])}
- **Year:** {summary.get('year', int(record['Year']))}
- **Talukas covered:** {summary.get('talukas', data['Taluka'].nunique())}
- **Average recharge:** {summary.get('avg_recharge', format_number(record['Annual Recharge (MCM)']))} MCM
- **Average extraction:** {summary.get('avg_extraction', format_number(record['Total Extraction (MCM)']))} MCM
- **Average extraction stage:** {summary.get('avg_stage', format_number(record['Extraction Stage Numeric']))}%
- **Latest category:** {summary.get('latest_category', record['Groundwater Category'])}
"""

        if intent == "recharge" and "highest" in preprocess_query(query):
            row = self.df.loc[self.df["Annual Recharge (MCM)"].idxmax()]
            return (
                f"Highest recharge in the dataset: **{row['Taluka']}**, **{row['District']}** "
                f"({int(row['Year'])}) — **{format_number(row['Annual Recharge (MCM)'])} MCM**"
            )

        if intent == "extraction" and "highest" in preprocess_query(query):
            row = self.df.loc[self.df["Total Extraction (MCM)"].idxmax()]
            return (
                f"Highest extraction in the dataset: **{row['Taluka']}**, **{row['District']}** "
                f"({int(row['Year'])}) — **{format_number(row['Total Extraction (MCM)'])} MCM**"
            )

        return (
            "I can only answer using the JALNETRA groundwater dataset. "
            "Try asking about a district, taluka, trend, ranking, or forecast."
        )

    def answer(self, query: str) -> str:
        cleaned = preprocess_query(query)
        intent = detect_intent(cleaned)
        memory = self._memory()
        memory.remember("user", query)
        GENERAL_KNOWLEDGE = [
            "prime minister",
            "president",
            "climate change",
            "artificial intelligence",
            "weather",
            "cricket",
            "ipl",
            "stock market",
            "bitcoin",
        ]

        if any(word in cleaned for word in GENERAL_KNOWLEDGE):
            return (
                "This question is outside the available JALNETRA groundwater dataset. "
                "Please ask groundwater-related questions."
            )

        if intent == "help":
            response = self._handle_help()
        elif intent == "state":
            response = self._handle_state(cleaned)
        elif intent == "rank":
            response = self._handle_rank(cleaned)
        elif intent == "compare":
            response = self._handle_compare(cleaned)
        elif (
            intent == "trend"
            or "next 5" in cleaned
            or "5-year" in cleaned
            or "5 year" in cleaned
        ):
            response = (
                self._handle_trend(cleaned)
                if intent != "forecast"
                else self._handle_forecast(cleaned)
            )
        elif intent == "forecast":
            response = self._handle_forecast(cleaned)
        elif intent == "risk":
            response = self._handle_risk(cleaned)
        elif intent == "graph":
            response = self._handle_graph(cleaned)
        elif "category distribution" in cleaned:
            response = self._handle_category_distribution(cleaned)
        elif "correlation" in cleaned:
            response = self._handle_correlation()
        elif is_count_query(cleaned):
            response = self._handle_counts(cleaned)
        else:
            response = self._handle_entity_lookup(cleaned, intent)

        memory.remember("assistant", response)
        return response


def process_query(query: str, df: pd.DataFrame) -> str:
    """Process a user query and return a data-grounded response."""
    bot = JalnetraChatbot(df)
    return bot.answer(query)


def chatbot_ui(df: pd.DataFrame) -> None:
    """Streamlit chat UI."""
    st.markdown("### JALNETRA AI Assistant")
    st.caption(
        "Answers are generated only from project datasets and forecasting models."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I'm **JALNETRA**, your groundwater intelligence assistant. "
                    "Ask me about districts, talukas, trends, rankings, or future forecasts."
                ),
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask about groundwater data, trends, or forecasts...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response = process_query(prompt, df)
    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
