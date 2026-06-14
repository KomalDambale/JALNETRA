"""Natural language preprocessing and intent detection."""

from __future__ import annotations

import re

from rapidfuzz import process

LANGUAGE_MAP = {
    "पूर्व मानसून": "pre monsoon",
    "पूर्वमोसमी": "pre monsoon",
    "प्री मानसून": "pre monsoon",
    "उत्तर मानसून": "post monsoon",
    "पोस्ट मानसून": "post monsoon",
    "भविष्य": "forecast",
    "अंदाज": "forecast",
    "भविष्यवाणी": "forecast",
    "जिल्हा": "district",
    "तालुका": "taluka",
    "पुनर्भरण": "recharge",
    "उपसा": "extraction",
    "ऐतिहासिक": "historical",
    "कल": "trend",
    "ग्राफ": "graph",
    "आलेख": "graph",
    "जिला": "district",
    "तहसील": "taluka",
    "पूर्वानुमान": "forecast",
    "रिचार्ज": "recharge",
    "निकासी": "extraction",
    "रुझान": "trend",
    "prediction": "forecast",
    "future": "forecast",
    "forecasting": "forecast",
    "predict": "forecast",
    "compare": "compare",
    "comparison": "compare",
    "rank": "rank",
    "ranking": "rank",
    "top": "rank",
    "highest": "rank",
    "lowest": "rank",
    "risk": "risk",
    "state": "state",
    "maharashtra": "state",
}


def preprocess_query(query: str) -> str:
    text = str(query).lower().strip()
    for key, value in LANGUAGE_MAP.items():
        text = text.replace(key.lower(), value)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_year(query: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", query)
    return int(match.group(1)) if match else None


def extract_top_n(query: str, default: int = 10) -> int:
    match = re.search(r"\btop\s+(\d+)\b", query)
    if match:
        return int(match.group(1))
    return default


def extract_district(query: str, df) -> str | None:
    if "District" not in df.columns:
        return None

    districts = df["District"].dropna().astype(str).unique().tolist()
    lowered = query.lower()
    for district in districts:
        if district.lower() in lowered:
            return district

    match = process.extractOne(query, districts, score_cutoff=72)
    return match[0] if match else None


def extract_taluka(query: str, df) -> str | None:
    if "Taluka" not in df.columns:
        return None

    talukas = df["Taluka"].dropna().astype(str).unique().tolist()
    lowered = query.lower()
    for taluka in talukas:
        if taluka.lower() in lowered:
            return taluka

    match = process.extractOne(query, talukas, score_cutoff=78)
    return match[0] if match else None


def extract_state(query: str, df) -> str | None:
    if "State" not in df.columns:
        return None

    states = df["State"].dropna().astype(str).unique().tolist()
    lowered = query.lower()
    for state in states:
        if state.lower() in lowered:
            return state
    return None


def extract_districts_for_compare(query: str, df) -> list[str]:
    districts = df["District"].dropna().astype(str).unique().tolist()
    found = [district for district in districts if district.lower() in query.lower()]
    if len(found) >= 2:
        return found[:2]

    matches = process.extract(query, districts, limit=2, score_cutoff=75)
    return [match[0] for match in matches]


def detect_intent(query: str) -> str:
    text = preprocess_query(query)

    if any(word in text for word in ["forecast", "predict", "future", "2030", "2028", "2026", "next 5"]):
        return "forecast"
    if any(word in text for word in ["risk", "at risk", "danger", "critical districts"]):
        return "risk"
    if any(word in text for word in ["compare", "comparison", " vs ", "versus"]):
        return "compare"
    if any(word in text for word in ["rank", "ranking", "top ", "highest", "lowest", "bottom"]):
        return "rank"
    if any(word in text for word in ["trend", "historical", "over time", "year wise", "year-wise"]):
        return "trend"
    if any(word in text for word in ["graph", "chart", "plot", "visualization", "visualise", "visualize"]):
        return "graph"
    if "state" in text or "maharashtra" in text:
        return "state"
    if "pre monsoon" in text:
        return "pre_monsoon"
    if "post monsoon" in text:
        return "post_monsoon"
    if any(word in text for word in ["recharge", "annual recharge"]):
        return "recharge"
    if any(word in text for word in ["extractable", "extractable resource"]):
        return "extractable"
    if any(word in text for word in ["extraction", "withdrawal", "usage"]):
        return "extraction"
    if any(word in text for word in ["stage", "extraction stage"]):
        return "stage"
    if any(word in text for word in ["category", "safe", "critical", "semi-critical", "over-exploited", "over exploited"]):
        return "category"
    if any(word in text for word in ["data", "table", "records", "show", "list"]):
        return "data"
    if any(word in text for word in ["help", "example", "what can you"]):
        return "help"
    return "general"


def detect_metric(query: str) -> str | None:
    from utils import resolve_metric

    return resolve_metric(preprocess_query(query))


def is_ascending_rank(query: str) -> bool:
    text = preprocess_query(query)
    return any(word in text for word in ["lowest", "bottom", "least", "minimum", "min "])


def is_count_query(query: str) -> bool:
    text = preprocess_query(query)
    return any(word in text for word in ["how many", "count", "number of", "total "])


def detect_category_filter(query: str) -> str | None:
    text = preprocess_query(query)
    for category in ["over-exploited", "over exploited", "critical", "semi-critical", "safe"]:
        if category in text:
            return category.replace("over exploited", "over-exploited").title()
    return None
