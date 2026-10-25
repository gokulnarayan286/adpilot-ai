
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# ADPILOT AI — PERFORMANCE MARKETING ANALYTICS DASHBOARD
# ============================================================

st.set_page_config(
    page_title="AdPilot AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "campaigns.csv"

REQUIRED_COLUMNS = [
    "date",
    "campaign",
    "platform",
    "spend",
    "installs",
    "purchases",
    "revenue",
]

OPTIONAL_COLUMNS = [
    "impressions",
    "clicks",
    "campaign_type",
    "market",
]


# ============================================================
# THEME
# ============================================================

if "adpilot_theme" not in st.session_state:
    st.session_state.adpilot_theme = "Dark"

theme = st.session_state.adpilot_theme

if theme == "Dark":
    BG = "#0B1120"
    PANEL = "#111B2E"
    PANEL_ALT = "#172338"
    TEXT = "#F1F5F9"
    MUTED = "#AAB8CC"
    BORDER = "#293750"
    GRID = "#293750"
    ACCENT = "#60A5FA"
else:
    BG = "#F4F7FB"
    PANEL = "#FFFFFF"
    PANEL_ALT = "#EAF0F8"
    TEXT = "#172033"
    MUTED = "#536178"
    BORDER = "#D8E0EC"
    GRID = "#D8E0EC"
    ACCENT = "#2563EB"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}

    [data-testid="stSidebar"] {{
        background-color: {PANEL};
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stHeader"] {{
        background-color: {BG};
    }}

    h1, h2, h3, h4, p, label, span {{
        color: {TEXT};
    }}

    [data-testid="stMetric"] {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        padding: 18px;
        border-radius: 14px;
    }}

    [data-testid="stMetricLabel"] {{
        color: {MUTED} !important;
    }}

    [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-size: 13px;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-color: {BORDER};
    }}

    .ap-subtitle {{
        color: {MUTED};
        font-size: 14px;
        margin-top: -10px;
    }}

    .ap-card {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 10px;
    }}

    .ap-muted {{
        color: {MUTED};
        font-size: 13px;
    }}

    .ap-brand {{
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.8px;
    }}

    .stButton button, .stDownloadButton button {{
        border-radius: 9px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING AND CLEANING
# ============================================================

@st.cache_data
def load_data(file_path: str, modified_time: float) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    # Normalize column names.
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Your campaigns.csv file is missing these columns: "
            + ", ".join(missing)
        )

    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            if column in ("campaign_type", "market"):
                df[column] = "Unknown"
            else:
                df[column] = 0

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    for column in [
        "spend",
        "installs",
        "purchases",
        "revenue",
        "impressions",
        "clicks",
    ]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["campaign"] = df["campaign"].fillna("Unnamed campaign").astype(str)
    df["platform"] = df["platform"].fillna("Unknown").astype(str)
    df["campaign_type"] = df["campaign_type"].fillna("Unknown").astype(str)
    df["market"] = df["market"].fillna("Unknown").astype(str)

    # Prevent invalid negative counts/spend from distorting KPIs.
    for column in [
        "spend",
        "installs",
        "purchases",
        "revenue",
        "impressions",
        "clicks",
    ]:
        df[column] = df[column].clip(lower=0)

    return df.sort_values("date").reset_index(drop=True)


def money(value):
    return f"₹{value:,.0f}"


def number(value):
    return f"{value:,.0f}"


def percent(value):
    return f"{value:.2f}%"


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived metrics without dividing by zero."""
    result = df.copy()

    result["CPI"] = result.apply(
        lambda r: safe_divide(r["spend"], r["installs"]), axis=1
    )
    result["CPA"] = result.apply(
        lambda r: safe_divide(r["spend"], r["purchases"]), axis=1
    )
    result["ROAS"] = result.apply(
        lambda r: safe_divide(r["revenue"], r["spend"]), axis=1
    )
    result["CTR"] = result.apply(
        lambda r: safe_divide(r["clicks"], r["impressions"]) * 100,
        axis=1,
    )
    result["CVR"] = result.apply(
        lambda r: safe_divide(r["purchases"], r["clicks"]) * 100,
        axis=1,
    )
    result["Install-to-purchase rate"] = result.apply(
        lambda r: safe_divide(r["purchases"], r["installs"]) * 100,
        axis=1,
    )

    return result


def chart_layout(fig, height=350):
    fig.update_layout(
        height=height,
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, size=12),
        title_font=dict(color=TEXT, size=16),
        legend_title_font=dict(color=TEXT),
        margin=dict(l=15, r=15, t=55, b=15),
        hoverlabel=dict(font_color="#111827"),
    )
    fig.update_xaxes(
        gridcolor=GRID,
        linecolor=BORDER,
        zerolinecolor=GRID,
        title_font=dict(color=MUTED),
    )
    fig.update_yaxes(
        gridcolor=GRID,
        linecolor=BORDER,
        zerolinecolor=GRID,
        title_font=dict(color=MUTED),
    )
    return fig


def show_chart(fig, height=350):
    st.plotly_chart(
        chart_layout(fig, height),
        use_container_width=True,
        config={"displaylogo": False},
    )


def section_title(title, subtitle=None):
    st.subheader(title)
    if subtitle:
        st.markdown(
            f'<div class="ap-subtitle">{subtitle}</div>',
            unsafe_allow_html=True,
        )


def download_csv(df, filename, label="Download CSV"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=False,
    )


def aggregate_metrics(df, group_column):
    if df.empty:
        return pd.DataFrame()

    result = (
        df.groupby(group_column, dropna=False, as_index=False)
        .agg(
            spend=("spend", "sum"),
            installs=("installs", "sum"),
            purchases=("purchases", "sum"),
            revenue=("revenue", "sum"),
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
        )
    )

    result = add_metrics(result)
    return result


# ============================================================
# LOAD DATA
# ============================================================

st.sidebar.markdown(
    '<div class="ap-brand">🚀 AdPilot AI</div>',
    unsafe_allow_html=True,
)
st.sidebar.caption("Performance Marketing Intelligence")

st.sidebar.divider()

theme_choice = st.sidebar.selectbox(
    "Appearance",
    ["Dark", "Light"],
    index=0 if st.session_state.adpilot_theme == "Dark" else 1,
)

if theme_choice != st.session_state.adpilot_theme:
    st.session_state.adpilot_theme = theme_choice
    st.rerun()

if not DATA_FILE.exists():
    st.title("🚀 AdPilot AI")
    st.error(f"Could not find the data file: {DATA_FILE}")
    st.info(
        "Create a campaigns.csv file in the same folder as dashboard.py. "
        "It must contain: date, campaign, platform, spend, installs, "
        "purchases, revenue."
    )
    st.stop()

try:
    raw_df = load_data(str(DATA_FILE), DATA_FILE.stat().st_mtime)
except Exception as error:
    st.error(f"Unable to load campaigns.csv: {error}")
    st.stop()

if raw_df.empty:
    st.warning("The CSV contains no valid campaign rows.")
    st.stop()

if "date" not in raw_df.columns:
    st.error("The data file must include a valid date column.")
    st.stop()

df = add_metrics(raw_df)


# ============================================================
# GLOBAL FILTERS
# ============================================================

st.sidebar.subheader("Filters")

min_date = raw_df["date"].min().date()
max_date = raw_df["date"].max().date()

default_start = max(min_date, max_date - timedelta(days=29))

date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range
    end_date = date_range

platform_options = sorted(raw_df["platform"].unique().tolist())
campaign_options = sorted(raw_df["campaign"].unique().tolist())
market_options = sorted(raw_df["market"].unique().tolist())

selected_platforms = st.sidebar.multiselect(
    "Platforms",
    platform_options,
    default=platform_options,
)

selected_campaigns = st.sidebar.multiselect(
    "Campaigns",
    campaign_options,
    default=campaign_options,
)

selected_markets = st.sidebar.multiselect(
    "Markets",
    market_options,
    default=market_options,
)

filtered_df = raw_df[
    (raw_df["date"].dt.date >= start_date)
    & (raw_df["date"].dt.date <= end_date)
    & (raw_df["platform"].isin(selected_platforms))
    & (raw_df["campaign"].isin(selected_campaigns))
    & (raw_df["market"].isin(selected_markets))
].copy()

filtered_df = add_metrics(filtered_df)

st.sidebar.divider()
st.sidebar.caption(f"Data rows: {len(raw_df):,}")
st.sidebar.caption(f"Filtered rows: {len(filtered_df):,}")
st.sidebar.caption(f"Data source: {DATA_FILE.name}")


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

pages = [
    "Overview",
    "Ads",
    "Campaigns",
    "Audience",
    "Attribution",
    "Reports",
    "Alerts",
    "Settings",
]

page = st.sidebar.radio("Navigation", pages, index=0)


# ============================================================
# HEADER AND EMPTY STATE
# ============================================================

st.title("AdPilot AI")
st.markdown(
    '<div class="ap-subtitle">'
    "Your performance marketing command center"
    "</div>",
    unsafe_allow_html=True,
)

st.write("")

if filtered_df.empty:
    st.warning(
        "No campaign data matches your current filters. "
        "Try expanding the date range or selecting more platforms."
    )
    st.stop()


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":
    section_title(
        "Overview",
        "A consolidated view of acquisition performance across platforms.",
    )

    total_spend = filtered_df["spend"].sum()
    total_revenue = filtered_df["revenue"].sum()
    total_installs = filtered_df["installs"].sum()
    total_purchases = filtered_df["purchases"].sum()
    total_impressions = filtered_df["impressions"].sum()
    total_clicks = filtered_df["clicks"].sum()

    overall_cpi = safe_divide(total_spend, total_installs)
    overall_cpa = safe_divide(total_spend, total_purchases)
    overall_roas = safe_divide(total_revenue, total_spend)
    overall_ctr = safe_divide(total_clicks, total_impressions) * 100
    overall_cvr = safe_divide(total_purchases, total_clicks) * 100

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Spend", money(total_spend))
    k2.metric("Reported Revenue", money(total_revenue))
    k3.metric("Total Installs", number(total_installs))
    k4.metric("Total Purchases", number(total_purchases))

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Blended CPI", money(overall_cpi))
    k6.metric("Blended CPA", money(overall_cpa))
    k7.metric("Reported ROAS", f"{overall_roas:.2f}x")
    k8.metric("CTR", percent(overall_ctr))

    st.write("")

    # FIX: explicitly create the Date column before grouping.
    daily = (
        filtered_df.assign(Date=filtered_df["date"].dt.date)
        .groupby("Date", as_index=False)
        .agg(
            spend=("spend", "sum"),
            revenue=("revenue", "sum"),
            installs=("installs", "sum"),
            purchases=("purchases", "sum"),
        )
        .sort_values("Date")
    )

    left, right = st.columns(2)

    with left:
        fig = px.line(
            daily,
            x="Date",
            y=["spend", "revenue"],
            markers=True,
            title="Spend vs reported revenue",
            labels={
                "Date": "Date",
                "value": "Amount (₹)",
                "variable": "Metric",
            },
        )
        show_chart(fig)

    with right:
        platform_summary = aggregate_metrics(filtered_df, "platform")
        fig = px.bar(
            platform_summary,
            x="platform",
            y="spend",
            color="platform",
            title="Spend by platform",
            labels={"platform": "Platform", "spend": "Spend (₹)"},
        )
        show_chart(fig)

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="installs",
            color="platform",
            title="Installs by platform",
            labels={"platform": "Platform", "installs": "Installs"},
        )
        show_chart(fig)

    with right:
        fig = px.scatter(
            platform_summary,
            x="spend",
            y="revenue",
            size="purchases",
            color="platform",
            hover_name="platform",
            title="Spend vs revenue by platform",
            labels={"spend": "Spend (₹)", "revenue": "Revenue (₹)"},
        )
        show_chart(fig)

    st.write("")
    section_title("Platform performance")

    display_cols = [
        "platform",
        "spend",
        "revenue",
        "installs",
        "purchases",
        "CPI",
        "CPA",
        "ROAS",
    ]

    platform_table = platform_summary[display_cols].copy()
    platform_table["spend"] = platform_table["spend"].map(money)
    platform_table["revenue"] = platform_table["revenue"].map(money)
    platform_table["CPI"] = platform_table["CPI"].map(money)
    platform_table["CPA"] = platform_table["CPA"].map(money)
    platform_table["ROAS"] = platform_table["ROAS"].map(
        lambda x: f"{x:.2f}x"
    )

    st.dataframe(platform_table, use_container_width=True, hide_index=True)


# ============================================================
# ADS
# ============================================================

elif page == "Ads":
    section_title(
        "Ads performance",
        "Compare traffic, costs, conversion rates, and return.",
    )

    total_spend = filtered_df["spend"].sum()
    total_impressions = filtered_df["impressions"].sum()
    total_clicks = filtered_df["clicks"].sum()
    total_installs = filtered_df["installs"].sum()
    total_purchases = filtered_df["purchases"].sum()
    total_revenue = filtered_df["revenue"].sum()

    a, b, c, d = st.columns(4)
    a.metric("Impressions", number(total_impressions))
    b.metric("Clicks", number(total_clicks))
    c.metric("CTR", percent(safe_divide(total_clicks, total_impressions) * 100))
    d.metric("Click-to-purchase CVR", percent(safe_divide(total_purchases, total_clicks) * 100))

    a, b, c, d = st.columns(4)
    a.metric("Spend", money(total_spend))
    b.metric("CPI", money(safe_divide(total_spend, total_installs)))
    c.metric("CPA", money(safe_divide(total_spend, total_purchases)))
    d.metric("ROAS", f"{safe_divide(total_revenue, total_spend):.2f}x")

    platform_summary = aggregate_metrics(filtered_df, "platform")

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="CPI",
            color="platform",
            title="Cost per install by platform",
        )
        show_chart(fig)

    with right:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="CPA",
            color="platform",
            title="Cost per purchase by platform",
        )
        show_chart(fig)

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="ROAS",
            color="platform",
            title="Reported ROAS by platform",
        )
        show_chart(fig)

    with right:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="CTR",
            color="platform",
            title="CTR by platform",
        )
        show_chart(fig)

    st.subheader("Detailed ads data")
    st.dataframe(
        filtered_df[
            [
                "date",
                "platform",
                "campaign",
                "spend",
                "impressions",
                "clicks",
                "installs",
                "purchases",
                "revenue",
                "CPI",
                "CPA",
                "ROAS",
                "CTR",
                "CVR",
            ]
        ].sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    download_csv(filtered_df, "adpilot_ads_data.csv", "Download ads data")


# ============================================================
# CAMPAIGNS
# ============================================================

elif page == "Campaigns":
    section_title(
        "Campaign analysis",
        "Find the campaigns driving results and the campaigns that need attention.",
    )

    campaign_summary = aggregate_metrics(filtered_df, "campaign")

    if campaign_summary.empty:
        st.info("No campaign data available.")
    else:
        top_campaigns = campaign_summary.sort_values(
            "revenue", ascending=False
        ).head(10)

        left, right = st.columns(2)

        with left:
            fig = px.bar(
                top_campaigns.sort_values("spend", ascending=True),
                x="spend",
                y="campaign",
                orientation="h",
                title="Top campaigns by reported revenue",
                color="platform" if "platform" in top_campaigns.columns else None,
            )
            show_chart(fig)

        with right:
            fig = px.scatter(
                campaign_summary,
                x="spend",
                y="revenue",
                size="purchases",
                hover_name="campaign",
                title="Campaign spend vs reported revenue",
                labels={"spend": "Spend (₹)", "revenue": "Revenue (₹)"},
            )
            show_chart(fig)

        st.subheader("Campaign performance table")

        sort_choice = st.selectbox(
            "Sort campaigns by",
            ["Spend", "Revenue", "Installs", "Purchases", "CPI", "CPA", "ROAS"],
        )

        sort_map = {
            "Spend": "spend",
            "Revenue": "revenue",
            "Installs": "installs",
            "Purchases": "purchases",
            "CPI": "CPI",
            "CPA": "CPA",
            "ROAS": "ROAS",
        }

        sorted_campaigns = campaign_summary.sort_values(
            sort_map[sort_choice],
            ascending=(sort_choice in ["CPI", "CPA"]),
        )

        st.dataframe(
            sorted_campaigns,
            use_container_width=True,
            hide_index=True,
        )

        download_csv(
            sorted_campaigns,
            "adpilot_campaign_report.csv",
            "Download campaign report",
        )


# ============================================================
# AUDIENCE
# ============================================================

elif page == "Audience":
    section_title(
        "Audience and market analysis",
        "Explore performance by market and campaign type when those fields exist in your CSV.",
    )

    left, right = st.columns(2)

    market_summary = aggregate_metrics(filtered_df, "market")
    type_summary = aggregate_metrics(filtered_df, "campaign_type")

    with left:
        fig = px.bar(
            market_summary,
            x="market",
            y="spend",
            color="market",
            title="Spend by market",
        )
        show_chart(fig)

    with right:
        fig = px.bar(
            market_summary,
            x="market",
            y="purchases",
            color="market",
            title="Purchases by market",
        )
        show_chart(fig)

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            type_summary,
            x="campaign_type",
            y="spend",
            color="campaign_type",
            title="Spend by campaign type",
        )
        show_chart(fig)

    with right:
        fig = px.bar(
            type_summary,
            x="campaign_type",
            y="ROAS",
            color="campaign_type",
            title="Reported ROAS by campaign type",
        )
        show_chart(fig)

    st.subheader("Market-level metrics")
    st.dataframe(market_summary, use_container_width=True, hide_index=True)

    st.subheader("Campaign-type metrics")
    st.dataframe(type_summary, use_container_width=True, hide_index=True)


# ============================================================
# ATTRIBUTION
# ============================================================

elif page == "Attribution":
    section_title(
        "Attribution overview",
        "Review reported acquisition outcomes. These figures use the CSV's recorded attribution and are not an incrementality test.",
    )

    total_installs = filtered_df["installs"].sum()
    total_purchases = filtered_df["purchases"].sum()
    total_spend = filtered_df["spend"].sum()
    total_revenue = filtered_df["revenue"].sum()

    a, b, c, d = st.columns(4)
    a.metric("Installs", number(total_installs))
    b.metric("Purchases", number(total_purchases))
    c.metric(
        "Install-to-purchase rate",
        percent(safe_divide(total_purchases, total_installs) * 100),
    )
    d.metric("Reported ROAS", f"{safe_divide(total_revenue, total_spend):.2f}x")

    platform_summary = aggregate_metrics(filtered_df, "platform")

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="installs",
            color="platform",
            title="Attributed installs by platform",
        )
        show_chart(fig)

    with right:
        fig = px.bar(
            platform_summary,
            x="platform",
            y="purchases",
            color="platform",
            title="Recorded purchases by platform",
        )
        show_chart(fig)

    # FIX: explicitly create Date before grouping.
    daily = (
        filtered_df.assign(Date=filtered_df["date"].dt.date)
        .groupby("Date", as_index=False)
        .agg(
            installs=("installs", "sum"),
            purchases=("purchases", "sum"),
        )
        .sort_values("Date")
    )

    fig = px.line(
        daily,
        x="Date",
        y=["installs", "purchases"],
        markers=True,
        title="Daily installs vs purchases",
        labels={
            "Date": "Date",
            "value": "Count",
            "variable": "Metric",
        },
    )
    show_chart(fig)

    st.info(
        "For incrementality, use a suitable holdout, geo experiment, "
        "or lift study. Attributed conversions alone do not prove that "
        "advertising caused those conversions."
    )


# ============================================================
# REPORTS
# ============================================================

elif page == "Reports":
    section_title(
        "Reports",
        "Build and export a performance report from the current filters.",
    )

    total_spend = filtered_df["spend"].sum()
    total_revenue = filtered_df["revenue"].sum()
    total_installs = filtered_df["installs"].sum()
    total_purchases = filtered_df["purchases"].sum()

    report = pd.DataFrame(
        [
            {"Metric": "Spend", "Value": total_spend},
            {"Metric": "Reported revenue", "Value": total_revenue},
            {"Metric": "Installs", "Value": total_installs},
            {"Metric": "Purchases", "Value": total_purchases},
            {
                "Metric": "CPI",
                "Value": safe_divide(total_spend, total_installs),
            },
            {
                "Metric": "CPA",
                "Value": safe_divide(total_spend, total_purchases),
            },
            {
                "Metric": "ROAS",
                "Value": safe_divide(total_revenue, total_spend),
            },
        ]
    )

    st.subheader("Executive summary")

    st.markdown(
        f"""
        <div class="ap-card">
            <h4>Performance snapshot</h4>
            <p>Reporting period: <b>{start_date}</b> to <b>{end_date}</b></p>
            <p>Total spend: <b>{money(total_spend)}</b></p>
            <p>Reported revenue: <b>{money(total_revenue)}</b></p>
            <p>Installs: <b>{number(total_installs)}</b></p>
            <p>Purchases: <b>{number(total_purchases)}</b></p>
            <p>Blended CPI: <b>{money(safe_divide(total_spend, total_installs))}</b></p>
            <p>Blended CPA: <b>{money(safe_divide(total_spend, total_purchases))}</b></p>
            <p>Reported ROAS: <b>{safe_divide(total_revenue, total_spend):.2f}x</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Platform report")
    platform_report = aggregate_metrics(filtered_df, "platform")
    st.dataframe(platform_report, use_container_width=True, hide_index=True)

    st.subheader("Campaign report")
    campaign_report = aggregate_metrics(filtered_df, "campaign")
    st.dataframe(campaign_report, use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        download_csv(report, "adpilot_executive_summary.csv", "Executive summary CSV")

    with col2:
        download_csv(platform_report, "adpilot_platform_report.csv", "Platform report CSV")

    with col3:
        download_csv(campaign_report, "adpilot_campaign_report.csv", "Campaign report CSV")


# ============================================================
# ALERTS
# ============================================================

elif page == "Alerts":
    section_title(
        "Alerts and opportunities",
        "Rule-based checks identify areas to investigate. They are not causal diagnoses.",
    )

    campaign_summary = aggregate_metrics(filtered_df, "campaign")

    if campaign_summary.empty:
        st.info("No campaign data available for alert analysis.")
    else:
        avg_cpi = safe_divide(
            filtered_df["spend"].sum(),
            filtered_df["installs"].sum(),
        )
        avg_cpa = safe_divide(
            filtered_df["spend"].sum(),
            filtered_df["purchases"].sum(),
        )
        avg_roas = safe_divide(
            filtered_df["revenue"].sum(),
            filtered_df["spend"].sum(),
        )

        alerts = []

        for _, row in campaign_summary.iterrows():
            campaign_name = row["campaign"]

            if row["spend"] > 0 and row["installs"] == 0:
                alerts.append(
                    {
                        "Severity": "High",
                        "Campaign": campaign_name,
                        "Finding": "Spend recorded but no installs recorded",
                        "Suggested check": (
                            "Check campaign objective, delivery, "
                            "tracking, and attribution windows."
                        ),
                    }
                )

            if row["spend"] > 0 and row["purchases"] == 0:
                alerts.append(
                    {
                        "Severity": "Medium",
                        "Campaign": campaign_name,
                        "Finding": "Spend recorded but no purchases recorded",
                        "Suggested check": (
                            "Check conversion tracking, traffic quality, "
                            "and the conversion funnel."
                        ),
                    }
                )

            if avg_cpi > 0 and row["installs"] > 0 and row["CPI"] > avg_cpi * 1.5:
                alerts.append(
                    {
                        "Severity": "Medium",
                        "Campaign": campaign_name,
                        "Finding": "CPI is more than 50% above blended CPI",
                        "Suggested check": (
                            "Review auction costs, creative performance, "
                            "audience mix, and install quality."
                        ),
                    }
                )

            if avg_cpa > 0 and row["purchases"] > 0 and row["CPA"] > avg_cpa * 1.5:
                alerts.append(
                    {
                        "Severity": "Medium",
                        "Campaign": campaign_name,
                        "Finding": "CPA is more than 50% above blended CPA",
                        "Suggested check": (
                            "Inspect purchase rate, product mix, "
                            "landing page, and conversion tracking."
                        ),
                    }
                )

            if row["spend"] > 0 and row["ROAS"] < 1:
                alerts.append(
                    {
                        "Severity": "Review",
                        "Campaign": campaign_name,
                        "Finding": "Reported ROAS is below 1.0x",
                        "Suggested check": (
                            "Validate revenue attribution, margin, "
                            "conversion lag, and campaign objective."
                        ),
                    }
                )

        if alerts:
            alerts_df = pd.DataFrame(alerts)

            high_count = (alerts_df["Severity"] == "High").sum()
            medium_count = (alerts_df["Severity"] == "Medium").sum()
            review_count = (alerts_df["Severity"] == "Review").sum()

            a, b, c = st.columns(3)
            a.metric("High priority", int(high_count))
            b.metric("Medium priority", int(medium_count))
            c.metric("Review", int(review_count))

            st.dataframe(alerts_df, use_container_width=True, hide_index=True)

            download_csv(alerts_df, "adpilot_alerts.csv", "Download alerts")
        else:
            st.success("No alerts were triggered by the current rules.")

        st.divider()
        st.subheader("Blended benchmarks")

        a, b, c = st.columns(3)
        a.metric("Blended CPI", money(avg_cpi))
        b.metric("Blended CPA", money(avg_cpa))
        c.metric("Blended ROAS", f"{avg_roas:.2f}x")

        st.caption(
            "Benchmarks are calculated from the selected rows. "
            "A high cost or low ROAS is a signal to investigate, not "
            "proof that a campaign should be paused."
        )


# ============================================================
# SETTINGS
# ============================================================

elif page == "Settings":
    section_title(
        "Settings",
        "Review your data source, fields, and dashboard configuration.",
    )

    st.subheader("Data source")
    st.write(f"**File:** `{DATA_FILE}`")
    st.write(f"**Rows:** {len(raw_df):,}")
    st.write(f"**Date range:** {min_date} to {max_date}")
    st.write(f"**Platforms:** {', '.join(platform_options)}")

    st.subheader("Required CSV columns")
    st.code(
        "date,campaign,platform,spend,installs,purchases,revenue",
        language="text",
    )

    st.subheader("Optional CSV columns")
    st.code(
        "impressions,clicks,campaign_type,market",
        language="text",
    )

    st.subheader("Detected columns")
    st.dataframe(
        pd.DataFrame(
            {
                "Column": raw_df.columns,
                "Data type": [str(raw_df[c].dtype) for c in raw_df.columns],
                "Missing values": [int(raw_df[c].isna().sum()) for c in raw_df.columns],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Metric definitions")

    definitions = pd.DataFrame(
        [
            {"Metric": "CPI", "Definition": "Spend ÷ installs"},
            {"Metric": "CPA", "Definition": "Spend ÷ purchases"},
            {"Metric": "ROAS", "Definition": "Reported revenue ÷ spend"},
            {"Metric": "CTR", "Definition": "Clicks ÷ impressions × 100"},
            {"Metric": "CVR", "Definition": "Purchases ÷ clicks × 100"},
            {
                "Metric": "Install-to-purchase rate",
                "Definition": "Purchases ÷ installs × 100",
            },
        ]
    )
    st.dataframe(definitions, use_container_width=True, hide_index=True)

    if st.button("Refresh CSV data", use_container_width=True):
        load_data.clear()
        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_left, footer_right = st.columns(2)

with footer_left:
    st.caption("AdPilot AI · Performance Marketing Intelligence")

with footer_right:
    st.caption(
        f"Reporting period: {start_date} — {end_date}"
    )
