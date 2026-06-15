from __future__ import annotations

import logging
import random
import smtplib
import tomllib
from email.mime.text import MIMEText
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

from analytics import DataQueryEngine
from chatbot import chatbot_ui
from config import (
    APP_NAME,
    COL_CATEGORY,
    COL_DISTRICT,
    COL_TALUKA,
    COL_YEAR,
    SECRETS_PATH,
    STYLE_PATH,
)
from data_loader import get_data_summary, load_master_dataframe
from forecasting import forecast_district
from pages.reports import generate_report
from prediction import models_available
from utils import copy_df, load_css
from visualization import (
    category_metrics,
    download_buttons,
    forecast_chart,
    trend_chart,
)
from ui_enhancements import (
    HOME_HERO,
    AI_BAND,
    LOGIN_CARD,
    topbar_html,
    page_header,
    forecast_kpi_cards,
    PLOTLY_THEME,
    SIDEBAR_BRAND,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)
if "otp" not in st.session_state:
    st.session_state.otp = ""

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False

if "page" not in st.session_state:
    st.session_state.page = "landing"
st.markdown(
    """
<script>
document.addEventListener('contextmenu', event => event.preventDefault());

document.addEventListener('keydown', function(e) {

    if (e.ctrlKey && e.key.toLowerCase() === 'c') {
        e.preventDefault();
    }

    if (e.ctrlKey && e.key.toLowerCase() === 'u') {
        e.preventDefault();
    }

    if (e.ctrlKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
    }

});
</script>
""",
    unsafe_allow_html=True,
)
st.markdown(
    '<style>[data-testid="stSidebarNav"]{display:none;}</style>', unsafe_allow_html=True
)

css = load_css(str(STYLE_PATH))
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "page": "home",
        "logged_in": False,
        "otp": "",
        "otp_sent": False,
        "user_email": "",
        "messages": [
            {
                "role": "assistant",
                "content": "Hello, I am JALNETRA. Ask me anything about your groundwater data.",
            }
        ],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_email_credentials() -> tuple[str, str]:
    email_address, email_password = "", ""
    try:
        email_address = st.secrets.get("EMAIL_ADDRESS", "")
        email_password = st.secrets.get("EMAIL_PASSWORD", "")
    except Exception:
        pass
    if (not email_address or not email_password) and SECRETS_PATH.exists():
        try:
            with SECRETS_PATH.open("rb") as f:
                secrets = tomllib.load(f)
            email_address = secrets.get("EMAIL_ADDRESS", "")
            email_password = secrets.get("EMAIL_PASSWORD", "")
        except Exception as exc:
            st.error(f"Could not read secrets: {exc}")
    return str(email_address).strip(), str(email_password).replace(" ", "").strip()


def send_otp(receiver_email: str) -> bool:
    otp = str(random.randint(100000, 999999))
    st.session_state.otp = otp
    st.session_state.otp_sent = False
    st.session_state.user_email = receiver_email
    email_address, email_password = get_email_credentials()
    # st.write("EMAIL =", email_address)
    # st.write("PASSWORD FOUND =", bool(email_password))
    if not email_address or not email_password:
        st.error(
            "Email OTP is not configured. Add credentials to .streamlit/secrets.toml"
        )
        return False
    message = MIMEText(
        f"Your OTP for {APP_NAME} login is:\n\n{otp}\n\nDo not share this OTP.",
        "plain",
        "utf-8",
    )
    message["Subject"] = f"{APP_NAME} OTP Verification"
    message["From"] = email_address
    message["To"] = receiver_email
    try:
        st.write("EMAIL:", email_address)
        st.write("PASSWORD EXISTS:", bool(email_password))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            # st.write("SMTP Connected")
            server.starttls()
            # st.write("TLS Started")
            server.login(email_address, email_password)
            # st.write("Login Success")
            server.sendmail(email_address, receiver_email, message.as_string())
        # st.write("Mail Sent")

        st.session_state.otp_sent = True
        return True

    except Exception as exc:
        st.error(f"ERROR TYPE: {type(exc).__name__}")
        st.error(f"ERROR: {exc}")
        return False


def navigate(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# ── Public pages ───────────────────────────────────────────────────────────


def home_page() -> None:

    st.markdown(
        """
<style>

/* Hide sidebar completely */
[data-testid="stSidebar"]{
    display:none !important;
}

/* Remove reserved sidebar space */
section[data-testid="stSidebar"]{
    display:none !important;
}


/* Remove sidebar toggle */
[data-testid="collapsedControl"]{
    display:none !important;
}

/* Remove left margin */
.main .block-container{
    padding-left:1rem !important;
    padding-right:1rem !important;
    max-width:100% !important;
}

</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown(HOME_HERO, unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2.5, 1.1, 1.1, 2.5])
    with c2:
        if st.button("Get Started", use_container_width=True):
            navigate("login")
    with c3:
        if st.button("Sign In", use_container_width=True):
            navigate("login")
    st.markdown(
        '<div class="section-title">Powerful Features</div>', unsafe_allow_html=True
    )
    features = [
        (
            "🤖",
            "AI ChatBot",
            "Data-grounded RAG chatbot with conversation memory and ML forecasting.",
        ),
        (
            "📊",
            "Interactive Visualizations",
            "Dynamic Plotly charts for trends, rankings, and comparisons.",
        ),
        (
            "🔮",
            "Future Predictions",
            "XGBoost-powered forecasts with confidence scores.",
        ),
        (
            "🗄️",
            "Data Explorer",
            "Auto-loaded CSV/Excel datasets with validation and cleaning.",
        ),
        (
            "🌐",
            "Multilingual Support",
            "English, Hindi, and Marathi query understanding.",
        ),
        ("📥", "Export Center", "Download CSV, Excel, and PDF reports."),
    ]
    for row in range(0, len(features), 3):
        cols = st.columns(3)
        for col, (icon, title, text) in zip(cols, features[row : row + 3]):
            with col:
                st.markdown(
                    f'<div class="feature-card"><div class="feature-icon">{icon}</div>'
                    f"<h3>{title}</h3><p>{text}</p></div>",
                    unsafe_allow_html=True,
                )


def login_page() -> None:
    st.markdown(
        """
        <style>
        /* Hide sidebar and toggle on login page */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        button[kind="header"] {
            display: none !important;
        }

        /* Full-width layout */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 0 !important;
        }

        /* Dark gradient background for the entire login page */
        .stApp {
            background:
                radial-gradient(ellipse 80% 50% at 50% 100%, rgba(6,182,212,0.18) 0%, transparent 55%),
                linear-gradient(160deg, #0C1A35 0%, #0F2A4A 50%, #073451 100%) !important;
        }

        /* Make tab container look like a glass card */
        .stTabs {
            background: rgba(255, 255, 255, 0.97) !important;
            border-radius: 22px !important;
            padding: 1.5rem 1.5rem 2rem !important;
            box-shadow:
                0 0 0 1px rgba(14,165,233,0.1),
                0 24px 60px rgba(15,23,42,0.22),
                0 8px 24px rgba(14,165,233,0.08) !important;
            border: none !important;
        }

        /* Inputs inside the login card */
        .stTabs div[data-testid="stTextInput"] input {
            background: #F8FAFC !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 10px !important;
            min-height: 46px !important;
            color: #0F172A !important;
        }

        .stTabs div[data-testid="stTextInput"] input:focus {
            border-color: #0EA5E9 !important;
            box-shadow: 0 0 0 3px rgba(14,165,233,0.12) !important;
        }

        .stTabs div[data-testid="stTextInput"] label {
            color: #374151 !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── 2. Header — logo + title rendered above the column ───────
    # Replaces the old st.markdown with inline h1/h3 styles.
    # Uses .login-header CSS class from style.css.
    st.markdown(
        """
        <div class="login-header">
            <div class="login-logo">💧</div>
            <h1>JALNETRA</h1>
            <p>AI-Powered Groundwater Intelligence Platform<br>
               Verify your email to access the dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
        with login_tab:
            email = st.text_input(
                "Email", placeholder="Enter your email", key="login_email"
            )
            if st.button("Send OTP", use_container_width=True, key="send_login_otp"):
                if email.strip() and send_otp(email.strip()):
                    st.success("OTP sent successfully")
            otp = st.text_input("OTP", placeholder="Enter OTP", key="login_otp")
            if st.button("Login", use_container_width=True, key="login_btn"):
                if otp == st.session_state.otp:
                    st.session_state.logged_in = True
                    navigate("dashboard")
                    st.rerun()
                else:
                    st.error("Invalid OTP")
        with signup_tab:
            st.text_input("Full Name", key="signup_name")
            signup_email = st.text_input("Email", key="signup_email")
            if st.button("Send OTP", use_container_width=True, key="signup_send"):
                if send_otp(signup_email):
                    st.success("OTP sent")
            signup_otp = st.text_input("OTP", key="signup_otp")
            if st.button("Sign Up", use_container_width=True, key="signup_btn"):
                if signup_otp == st.session_state.otp:
                    st.session_state.logged_in = True
                    navigate("dashboard")
                    st.rerun()
                else:
                    st.error("Invalid OTP")


def topbar():
    st.markdown(
        topbar_html(st.session_state.get("user_email", "")),
        unsafe_allow_html=True,
    )
    st.caption(f"Authorized User: {st.session_state.get('user_email','Guest')}")


def sidebar_navigation() -> str:
    st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
    st.sidebar.markdown("## JALNETRA")
    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Groundwater Overview",
            "District Analysis",
            "Taluka Analysis",
            "Trend Analysis",
            "Future Prediction",
            "AI ChatBot",
            "Data Explorer",
            "Download Center",
            "Assessments",
            "Query History",
        ],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    summary = get_data_summary(load_master_dataframe())

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        navigate("home")
    return menu


# ── Dashboard pages ────────────────────────────────────────────────────────


def dashboard_page(df: pd.DataFrame) -> None:
    st.title("Groundwater Intelligence Dashboard")
    st.caption("Welcome to JALNETRA – your AI-powered groundwater data assistant")
    category_metrics(df)
    summary = get_data_summary(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", f"{summary['records']:,}")
    c2.metric("Districts", summary["districts"])
    c3.metric("Talukas", summary["talukas"])
    c4.metric("Years", f"{min(summary['years'])}–{max(summary['years'])}")
    st.info(
        "Use **AI ChatBot** for natural language queries or explore dedicated analysis pages from the sidebar."
    )


def overview_page(df: pd.DataFrame) -> None:
    st.markdown(
        page_header("🌊", "Groundwater Overview", "Statewide groundwater insights"),
        unsafe_allow_html=True,
    )
    engine = DataQueryEngine(df)
    result = engine.state_summary()
    st.markdown(result.answer)
    latest_year = int(df[COL_YEAR].max())
    year_df = df[df[COL_YEAR] == latest_year]
    fig = px.pie(
        year_df, names=COL_CATEGORY, title=f"Category Distribution ({latest_year})"
    )
    fig.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.bar(
        year_df.groupby(COL_DISTRICT, as_index=False)["Extraction Stage Numeric"]
        .mean()
        .sort_values("Extraction Stage Numeric", ascending=False)
        .head(15),
        x=COL_DISTRICT,
        y="Extraction Stage Numeric",
        title="Top 15 Districts by Extraction Stage",
    )
    fig2.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig2, use_container_width=True)


def district_analysis_page(df: pd.DataFrame) -> None:
    st.title("District Analysis")
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("Select District", districts)
    year = st.selectbox(
        "Year", ["Latest"] + sorted(df[COL_YEAR].unique(), reverse=True)
    )
    yr = None if year == "Latest" else int(year)
    engine = DataQueryEngine(df)
    result = engine.district_summary(district, year=yr)
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(
                result.data,
                ["Annual Recharge (MCM)", "Total Extraction (MCM)"],
                f"{district} Trends",
            ),
            use_container_width=True,
        )
        display_df = result.data.tail(15).copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)


def taluka_analysis_page(df: pd.DataFrame) -> None:
    st.title("Taluka Analysis")
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("District", districts, key="tal_district")
    talukas = sorted(df[df[COL_DISTRICT] == district][COL_TALUKA].dropna().unique())
    taluka = st.selectbox("Taluka", talukas)
    engine = DataQueryEngine(df)
    result = engine.taluka_summary(taluka)
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(
                result.data, ["Extraction Stage Numeric"], f"{taluka} Extraction Stage"
            ),
            use_container_width=True,
        )


def trend_analysis_page(df: pd.DataFrame) -> None:
    st.title("Trend Analysis")
    c1, c2, c3 = st.columns(3)
    with c1:
        district = st.selectbox("District", ["All"] + sorted(df[COL_DISTRICT].unique()))
    with c2:
        metric = st.selectbox(
            "Metric",
            [
                "Annual Recharge (MCM)",
                "Total Extraction (MCM)",
                "Extraction Stage Numeric",
            ],
        )
    with c3:
        y_from, y_to = st.slider(
            "Year Range", int(df[COL_YEAR].min()), int(df[COL_YEAR].max()), (2021, 2025)
        )
    filtered = copy_df(df)
    if district != "All":
        filtered = filtered[filtered[COL_DISTRICT] == district]
    filtered = filtered[(filtered[COL_YEAR] >= y_from) & (filtered[COL_YEAR] <= y_to)]
    engine = DataQueryEngine(filtered)
    result = engine.trend(
        metric_col=metric,
        district=None if district == "All" else district,
        year_from=y_from,
        year_to=y_to,
    )
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(filtered, [metric], f"Trend: {metric}"),
            use_container_width=True,
        )


def prediction_page(df: pd.DataFrame) -> None:
    st.title("Future Prediction Center")
    st.caption(
        "AI-generated forecasts using XGBoost ML models and historical trend analysis"
    )
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("District", districts, key="pred_district")
    horizon = st.slider("Forecast Horizon (years)", 1, 10, 5)
    if st.button("Generate Forecast", type="primary"):
        fc = forecast_district(df, district, horizon=horizon)
        if fc.empty:
            st.error("No data available for forecasting.")
            return
        st.warning(
            "⚠️ Results below are **AI-generated predictions**, not observed data."
        )
        display_df = fc.copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.plotly_chart(forecast_chart(fc, district), use_container_width=True)
        last = fc.iloc[-1]
        c1, c2, c3 = st.columns(3)
        st.markdown(
            forecast_kpi_cards(
                last["Predicted Stage"],
                last["Predicted Category"],
                last["Confidence Score"],
            ),
            unsafe_allow_html=True,
        )
        download_buttons(fc, f"forecast_{district}")


def data_explorer_page(df: pd.DataFrame) -> None:
    st.title("Data Explorer")
    c1, c2, c3 = st.columns(3)
    with c1:
        d = st.selectbox(
            "District", ["All"] + sorted(df[COL_DISTRICT].unique()), key="exp_d"
        )
    with c2:
        t = st.selectbox(
            "Taluka", ["All"] + sorted(df[COL_TALUKA].unique()), key="exp_t"
        )
    with c3:
        y = st.selectbox(
            "Year", ["All"] + sorted(df[COL_YEAR].unique(), reverse=True), key="exp_y"
        )
    filtered = copy_df(df)
    if d != "All":
        filtered = filtered[filtered[COL_DISTRICT] == d]
    if t != "All":
        filtered = filtered[filtered[COL_TALUKA] == t]
    if y != "All":
        filtered = filtered[filtered[COL_YEAR] == int(y)]
    st.metric("Matching Records", len(filtered))
    display_df = filtered.copy()

    if "Year" in display_df.columns:
        display_df["Year"] = display_df["Year"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def download_center_page(df: pd.DataFrame) -> None:
    st.title("Download Center")
    st.subheader("Export Dataset")
    download_buttons(df, "jalnetra_groundwater")
    st.subheader("Generate PDF Report")
    districts = sorted(df[COL_DISTRICT].unique())
    district = st.selectbox("District for PDF", districts, key="pdf_d")
    latest = df[df[COL_DISTRICT] == district].sort_values(COL_YEAR).iloc[-1]
    stage = latest.get(
        "Extraction Stage Numeric", latest.get("Extraction Stage (%)", 0)
    )
    if st.button("Generate PDF"):
        path = Path("exports") / f"report_{district}.pdf"
        path.parent.mkdir(exist_ok=True)
        result = generate_report(str(path), district, stage, latest[COL_CATEGORY])
        if result:
            with path.open("rb") as f:
                st.download_button(
                    "Download PDF Report",
                    f,
                    file_name=path.name,
                    mime="application/pdf",
                )
            st.success("Report generated.")
        else:
            st.error("Report generation failed.")


def assessments_page(df: pd.DataFrame) -> None:
    st.title("Assessment Units")
    search = st.text_input("Search by district, taluka, category, or year")
    category = st.selectbox(
        "Category", ["All", "Safe", "Semi-Critical", "Critical", "Over-Exploited"]
    )
    filtered = copy_df(df)
    if search:
        mask = filtered.astype(str).apply(
            lambda r: r.str.contains(search, case=False, na=False).any(), axis=1
        )
        filtered = filtered[mask]
    if category != "All":
        filtered = filtered[filtered[COL_CATEGORY] == category]
    cols = [
        COL_DISTRICT,
        COL_TALUKA,
        COL_YEAR,
        "Pre-Monsoon Level (mbgl)",
        "Post-Monsoon Level (mbgl)",
        "Annual Recharge (MCM)",
        "Extractable Resource (MCM)",
        "Total Extraction (MCM)",
        "Extraction Stage (%)",
        COL_CATEGORY,
    ]
    display_df = filtered[cols].copy()

    if "Year" in display_df.columns:
        display_df["Year"] = display_df["Year"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def query_history_page(df=None):
    if st.button("Clear History"):
        st.session_state.messages = []
        if "chat_memory" in st.session_state:
            st.session_state.chat_memory.history = []
        st.rerun()
    st.title("Query History")
    if not st.session_state.messages:
        st.info("No query history yet.")
        return
    for msg in st.session_state.messages:
        label = "User" if msg["role"] == "user" else APP_NAME
        st.markdown(f"### {label}\n\n{msg['content']}")
        st.divider()


def app_dashboard() -> None:
    df = load_master_dataframe()
    topbar()
    menu = sidebar_navigation()
    pages = {
        "Dashboard": dashboard_page,
        "Groundwater Overview": overview_page,
        "District Analysis": district_analysis_page,
        "Taluka Analysis": taluka_analysis_page,
        "Trend Analysis": trend_analysis_page,
        "Future Prediction": prediction_page,
        "AI ChatBot": lambda d: (st.title("AI Groundwater Assistant"), chatbot_ui(d)),
        "Data Explorer": data_explorer_page,
        "Download Center": download_center_page,
        "Assessments": assessments_page,
        "Query History": query_history_page,
    }
    handler = pages.get(menu, dashboard_page)
    handler(df)


def main() -> None:
    init_state()
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "dashboard":
        st.markdown(
            """
        <style>
        [data-testid="stSidebar"] {
        display:block;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )
        if not st.session_state.logged_in:
            navigate("login")
        else:
            app_dashboard()
    else:
        navigate("home")


if __name__ == "__main__":
    main()
