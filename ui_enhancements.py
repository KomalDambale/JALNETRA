# ═══════════════════════════════════════════════════════════════
# JALNETRA — UI Enhancement Guide for app.py
# Drop-in HTML/Python snippets (no logic changes)
# ═══════════════════════════════════════════════════════════════
#
# Replace only the st.markdown() / display sections in your app.py.
# All backend logic, models, and data calls stay unchanged.
# ───────────────────────────────────────────────────────────────


# ── 1. HOME PAGE HERO ──────────────────────────────────────────
# Replace the existing hero st.markdown() call with:

HOME_HERO = """
<div class="hero">
    <div class="hero-content">
        <div class="hero-badge">💧 AI-Driven Virtual Assistant for INGRES</div>
        <h1>JALNETRA</h1>
        <h2>Smart Groundwater Monitoring &amp; Forecasting System</h2>
        <p>
            Intelligent groundwater resource management powered by XGBoost ML,
            RAG-based AI, and real-time analytics across Maharashtra's districts and talukas.
        </p>
        <div class="hero-stats">
            <div class="hero-stat">
                <div class="hero-stat-value">36+</div>
                <div class="hero-stat-label">Districts</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-value">350+</div>
                <div class="hero-stat-label">Talukas</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-value">2021–30</div>
                <div class="hero-stat-label">Data Range</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-stat">
                <div class="hero-stat-value">XGBoost</div>
                <div class="hero-stat-label">ML Engine</div>
            </div>
        </div>
    </div>
</div>
"""

# ── 2. HOME PAGE AI BRANDING BAND ──────────────────────────────
# Add below the feature cards section:

AI_BAND = """
<div class="ai-band">
    <div>
        <div class="ai-band-title">Powered by AI &amp; Machine Learning</div>
        <div class="ai-band-sub">
            JALNETRA combines XGBoost forecasting, RAG-based retrieval, NLP query
            understanding, and Plotly analytics into a unified groundwater intelligence
            platform — built as a Final Year CSE Engineering Project.
        </div>
        <div class="ai-band-tech">
            <span class="tech-pill">XGBoost ML</span>
            <span class="tech-pill">RapidFuzz NLP</span>
            <span class="tech-pill">Plotly Analytics</span>
            <span class="tech-pill">Pandas</span>
            <span class="tech-pill">Streamlit</span>
            <span class="tech-pill">OTP Auth</span>
            <span class="tech-pill">Multilingual</span>
        </div>
    </div>
</div>
"""

# ── 3. LOGIN PAGE CARD ─────────────────────────────────────────
# Replace the login container HTML with:

LOGIN_CARD = """
<div class="login-container">
    <div class="login-card">
        <div class="login-logo">JN</div>
        <h1>JALNETRA</h1>
        <p>Groundwater Intelligence Platform<br>
           Enter your credentials to access the dashboard</p>
    </div>
</div>
"""
# Note: render this ABOVE the actual Streamlit tab/input widgets.
# Streamlit inputs must remain as st.text_input() / st.button() calls.


# ── 4. TOPBAR ──────────────────────────────────────────────────
# Replace the topbar() function's st.markdown with:


def topbar_html(email: str = "") -> str:
    return f"""
<div class="topbar">
    <div class="brand">💧 JALNETRA</div>
    <div class="topbar-right">
        <div class="topbar-dot"></div>
        <span>Live Data</span>
        {"&nbsp;·&nbsp;" + email if email else ""}
    </div>
</div>
"""


# Usage in topbar():
#   st.markdown(topbar_html(st.session_state.get("user_email", "")), unsafe_allow_html=True)


# ── 5. DASHBOARD PAGE HEADER ───────────────────────────────────
# Replace st.title() calls on every page with this pattern:


def page_header(icon: str, title: str, subtitle: str = "") -> str:
    return f"""
<div class="page-header">
    <div class="page-header-icon">{icon}</div>
    <div>
        <div class="page-header-title">{title}</div>
        {"" if not subtitle else f'<div class="page-header-sub">{subtitle}</div>'}
    </div>
</div>
"""


# Example replacements:
#   st.title("Dashboard")          →  st.markdown(page_header("📊", "Dashboard", "Executive groundwater overview"), unsafe_allow_html=True)
#   st.title("AI ChatBot")         →  st.markdown(page_header("🤖", "AI Groundwater Assistant", "Powered by JALNETRA NLP Engine"), unsafe_allow_html=True)
#   st.title("Future Prediction")  →  st.markdown(page_header("🔮", "Future Prediction Center", "XGBoost forecasts · 2026–2030"), unsafe_allow_html=True)
#   st.title("Trend Analysis")     →  st.markdown(page_header("📈", "Trend Analysis", "Historical groundwater patterns"), unsafe_allow_html=True)
#   st.title("Data Explorer")      →  st.markdown(page_header("🗄️", "Data Explorer", "Browse and filter the full dataset"), unsafe_allow_html=True)
#   st.title("Download Center")    →  st.markdown(page_header("📥", "Download Center", "Export data and generate PDF reports"), unsafe_allow_html=True)
#   st.title("Assessment Units")   →  st.markdown(page_header("📋", "Assessment Units", "Search and filter all groundwater assessments"), unsafe_allow_html=True)
#   st.title("Query History")      →  st.markdown(page_header("🕘", "Query History", "Your recent AI assistant conversations"), unsafe_allow_html=True)


# ── 6. FORECAST PREDICTION CARDS ──────────────────────────────
# In prediction_page(), replace the c1/c2/c3 metric block with:


def forecast_kpi_cards(stage: float, category: str, confidence: float) -> str:
    stage_class = (
        "safe"
        if stage < 70
        else "semi" if stage < 90 else "critical" if stage < 100 else "over"
    )
    risk_class = {
        "Safe": "risk-safe",
        "Semi-Critical": "risk-semi",
        "Critical": "risk-critical",
        "Over-Exploited": "risk-over",
    }.get(category, "risk-safe")

    return f"""
<div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr); margin-top:1.25rem;">
    <div class="forecast-card">
        <div class="forecast-card-label">Predicted Extraction Stage</div>
        <div class="forecast-card-value {stage_class}">{stage:.1f}%</div>
        <div class="forecast-card-sub">Forecast value</div>
    </div>
    <div class="forecast-card">
        <div class="forecast-card-label">Groundwater Category</div>
        <div class="forecast-card-value" style="font-size:1.6rem;">{category}</div>
        <span class="risk-badge {risk_class}">{category}</span>
    </div>
    <div class="forecast-card">
        <div class="forecast-card-label">Model Confidence</div>
        <div class="forecast-card-value" style="color:#34D399;">{confidence:.1f}%</div>
        <span class="confidence-badge">✓ XGBoost</span>
    </div>
</div>
"""


# In prediction_page(), replace:
#   c1.metric("Predicted Stage", ...)
#   c2.metric("Category", ...)
#   c3.metric("Confidence", ...)
# With:
#   st.markdown(forecast_kpi_cards(last['Predicted Stage'], last['Predicted Category'], last['Confidence Score']), unsafe_allow_html=True)


# ── 7. PLOTLY CHART THEME ──────────────────────────────────────
# Add this helper to visualization.py and wrap every fig with it:


PLOTLY_THEME = dict(
    template="plotly_white",
    font=dict(
        family="Inter, sans-serif",
        color="#000000",
        size=13,
    ),
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    margin=dict(
        l=16,
        r=16,
        t=48,
        b=16,
    ),
    title=dict(
        font=dict(
            family="Space Grotesk, sans-serif",
            size=18,
            color="#000000",
        ),
        x=0.02,
        xanchor="left",
    ),
    legend=dict(
        bgcolor="#FFFFFF",
        bordercolor="#94A3B8",
        borderwidth=1,
        font=dict(
            size=12,
            color="#000000",
        ),
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor="#CBD5E1",
        gridwidth=1,
        zeroline=False,
        tickfont=dict(
            size=12,
            color="#000000",
        ),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#CBD5E1",
        gridwidth=1,
        zeroline=False,
        tickfont=dict(
            size=12,
            color="#000000",
        ),
    ),
    colorway=[
        "#0284C7",  # Blue
        "#10B981",  # Green
        "#F59E0B",  # Orange
        "#EF4444",  # Red
        "#7C3AED",  # Purple
    ],
)

# Usage: fig.update_layout(**PLOTLY_THEME)
# Or add a helper:
# def apply_theme(fig):
#     fig.update_layout(**PLOTLY_THEME)
#     return fig


# ── 8. CHATBOT UI HEADER ──────────────────────────────────────
# In chatbot_ui(), replace the st.markdown("### JALNETRA AI Assistant") with:

CHATBOT_HEADER = """
<div class="chat-header">
    <div class="chat-avatar-ai">🤖</div>
    <div>
        <div class="chat-header-title">JALNETRA AI Assistant</div>
        <div class="chat-header-sub">Groundwater Intelligence · Data-Grounded Responses</div>
    </div>
    <div class="chat-online">
        <div class="chat-online-dot"></div>
        Online
    </div>
</div>
"""

# Usage:
#   st.markdown(CHATBOT_HEADER, unsafe_allow_html=True)
#   st.caption("Answers generated only from project datasets and forecasting models.")


# ── 9. SIDEBAR NAVIGATION ─────────────────────────────────────
# In sidebar_navigation(), add this at the top of the sidebar before radio:

SIDEBAR_BRAND = """
<div class="sidebar-brand">
    <div class="sidebar-brand-title">💧 JALNETRA</div>
    <div class="sidebar-brand-sub">Water Intelligence Platform</div>
</div>
"""

SIDEBAR_SECTION_ANALYTICS = '<div class="sidebar-section-label">Analytics</div>'
SIDEBAR_SECTION_AI = '<div class="sidebar-section-label">AI Tools</div>'
SIDEBAR_SECTION_DATA = '<div class="sidebar-section-label">Data</div>'

# Usage in sidebar_navigation():
#   with st.sidebar:
#       st.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
#       st.markdown(SIDEBAR_SECTION_ANALYTICS, unsafe_allow_html=True)
#       ... (Dashboard, Overview, District, Taluka, Trend radio options)
#       st.markdown(SIDEBAR_SECTION_AI, unsafe_allow_html=True)
#       ... (Future Prediction, AI ChatBot, Query History radio options)
#       st.markdown(SIDEBAR_SECTION_DATA, unsafe_allow_html=True)
#       ... (Data Explorer, Download Center, Assessments radio options)


# ── 10. FEATURE CARDS (HOME) ───────────────────────────────────
# The existing feature_card HTML classes are already styled.
# Ensure your home_page() renders them exactly like this:

FEATURES = [
    (
        "🤖",
        "AI ChatBot",
        "Data-grounded RAG chatbot with conversation memory and XGBoost forecasting.",
    ),
    (
        "📊",
        "Interactive Analytics",
        "Dynamic Plotly charts for historical trends, rankings, and district comparisons.",
    ),
    (
        "🔮",
        "Future Predictions",
        "XGBoost-powered forecasts up to 2030 with confidence scores and risk levels.",
    ),
    (
        "🗄️",
        "Data Explorer",
        "Browse, filter, and search the complete INGRES groundwater dataset.",
    ),
    (
        "🌐",
        "Multilingual NLP",
        "Natural query understanding in English, Hindi, and Marathi.",
    ),
    (
        "📥",
        "Export Center",
        "Download filtered CSV, Excel datasets and generate district PDF reports.",
    ),
]

# Keep your existing loop in home_page(); the CSS will style them automatically.


# ── 11. APP FOOTER ─────────────────────────────────────────────
# Add at the bottom of app_dashboard():

APP_FOOTER = """
<div class="app-footer">
    <strong>JALNETRA</strong> — AI-Driven Groundwater Monitoring &amp; Forecasting System<br>
    Final Year CSE Project · Built with Streamlit, XGBoost, RapidFuzz &amp; Plotly
</div>
"""
# st.markdown(APP_FOOTER, unsafe_allow_html=True)
