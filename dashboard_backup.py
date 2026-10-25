import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ============================================================
# ADPILOT AI | PERFORMANCE MARKETING INTELLIGENCE
# ============================================================

st.set_page_config(
    page_title="AdPilot AI | Marketing Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CONFIGURATION ----------------

CSV_FILE = Path(__file__).resolve().parent / "campaigns.csv"
TARGET_CPA = 80.0
TARGET_ROAS = 2.0

# ---------------- SESSION STATE ----------------

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

# ---------------- THEME ----------------

DARK = st.session_state.dark_mode

if DARK:
    BG = "#0b1018"
    SIDEBAR = "#080d14"
    CARD = "#141d29"
    TEXT = "#e5edf7"
    MUTED = "#9aabc0"
    BORDER = "#263447"
    GRID = "#1f2c3f"
    ACCENT = "#38bdf8"
    SECONDARY = "#2dd4bf"
    PURPLE = "#a78bfa"
    ORANGE = "#fb923c"
    TEMPLATE = "plotly_dark"
else:
    BG = "#f8fafc"
    SIDEBAR = "#ffffff"
    CARD = "#ffffff"
    TEXT = "#0f172a"
    MUTED = "#64748b"
    BORDER = "#e2e8f0"
    GRID = "#f1f5f9"
    ACCENT = "#0284c7"
    SECONDARY = "#0d9488"
    PURPLE = "#7c3aed"
    ORANGE = "#ea580c"
    TEMPLATE = "plotly_white"

# Custom CSS for executive UI/UX and non-truncating KPI metric sizing
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}

    [data-testid="stSidebar"] {{
        background-color: {SIDEBAR};
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stMetric"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 14px 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }}

    [data-testid="stMetricLabel"] {{
        color: {MUTED};
        font-weight: 600;
        font-size: 12px;
    }}

    [data-testid="stMetricValue"] {{
        color: {TEXT};
        font-weight: 700;
        font-size: 1.35rem !important; /* Prevents text truncation */
        white-space: nowrap;
        overflow: hidden;
        text-overflow: clip;
    }}

    h1, h2, h3, h4, p, label {{
        color: {TEXT};
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD};
        border-color: {BORDER};
        border-radius: 12px;
    }}

    div.stButton > button {{
        border-radius: 8px;
        font-weight: 600;
    }}

    .eyebrow {{
        color: {ACCENT};
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }}

    .subtle {{
        color: {MUTED};
        font-size: 13px;
    }}

    /* Methodology Badges */
    .badge-fact {{
        background-color: rgba(45, 212, 191, 0.15);
        color: {SECONDARY};
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.5px;
    }}
    
    .badge-hypo {{
        background-color: rgba(251, 146, 60, 0.15);
        color: {ORANGE};
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.5px;
    }}

    .badge-action {{
        background-color: rgba(56, 189, 248, 0.15);
        color: {ACCENT};
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.5px;
    }}

    hr {{
        border-color: {BORDER};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- DATA LOADING ----------------

@st.cache_data
def load_data(file_path, modified_time):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required = {
        "date", "campaign", "platform", "spend",
        "installs", "purchases", "revenue"
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required CSV columns: {', '.join(sorted(missing))}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_columns = [
        "spend", "installs", "purchases", "revenue"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["impressions", "clicks"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.dropna(
        subset=[
            "date", "campaign", "platform", "spend",
            "installs", "purchases", "revenue"
        ]
    )

    if (
        (df[numeric_columns] < 0).any().any()
        or (df[["impressions", "clicks"]] < 0).any().any()
    ):
        raise ValueError("The CSV contains negative metric values.")

    return df


if not CSV_FILE.exists():
    st.error(
        f"Cannot find campaigns.csv at {CSV_FILE}. "
        "Place campaigns.csv in the same folder as app.py."
    )
    st.stop()

try:
    df = load_data(str(CSV_FILE), CSV_FILE.stat().st_mtime)
except Exception as error:
    st.error(f"Could not load campaign data: {error}")
    st.stop()

if df.empty:
    st.warning("The CSV contains no valid campaign records.")
    st.stop()

# ---------------- REUSABLE FUNCTIONS ----------------

def metrics(data):
    spend = data["spend"].sum()
    installs = data["installs"].sum()
    purchases = data["purchases"].sum()
    revenue = data["revenue"].sum()

    return {
        "spend": spend,
        "installs": installs,
        "purchases": purchases,
        "revenue": revenue,
        "cpi": spend / installs if installs > 0 else None,
        "cpa": spend / purchases if purchases > 0 else None,
        "roas": revenue / spend if spend > 0 else None,
        "conversion_rate": (
            purchases / installs * 100 if installs > 0 else None
        )
    }


def money(value, compact=False):
    """Formats monetary numbers. Supports compact mode for header KPI cards."""
    if value is None:
        return "N/A"
    
    if compact:
        abs_val = abs(value)
        if abs_val >= 10_000_000:
            return f"₹{value / 10_000_000:.2f} Cr"
        elif abs_val >= 100_000:
            return f"₹{value / 100_000:.2f} L"
        elif abs_val >= 1_000:
            return f"₹{value / 1_000:.1f} K"
            
    return f"₹{value:,.2f}"


def multiple(value):
    return "N/A" if value is None else f"{value:.2f}x"


def percent(value):
    return "N/A" if value is None else f"{value:.2f}%"


def style_chart(fig):
    fig.update_layout(
        template=TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="sans-serif"),
        margin=dict(l=10, r=10, t=45, b=10),
        legend_title_text="",
        hovermode="x unified"
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.markdown("## 🚀 AdPilot AI")
    st.caption("PERFORMANCE INTELLIGENCE")
    st.divider()

    st.toggle(
        "🌙 Dark mode",
        key="dark_mode",
        help="Switch between dark and light dashboard themes."
    )

    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "Ads",
            "Campaigns",
            "Audience",
            "Attribution",
            "Reports",
            "Alerts",
            "Settings"
        ],
        label_visibility="visible"
    )

    st.divider()
    st.caption("DATA SOURCE")
    st.success(f"{len(df):,} records loaded")
    st.caption("CSV analytics · Demo data")

    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------- HEADER ----------------

st.markdown(
    '<div class="eyebrow">MARKETING ANALYTICS PLATFORM</div>',
    unsafe_allow_html=True
)

st.title("Performance Dashboard")
st.caption(
    "Monitor campaign efficiency, compare performance vectors, and evaluate marketing incrementality."
)

# ---------------- FILTERS ----------------

with st.container(border=True):
    st.markdown("#### Filters")

    filter_col1, filter_col2, filter_col3 = st.columns([1.3, 1.3, 1])

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    with filter_col1:
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    with filter_col2:
        available_platforms = sorted(df["platform"].unique().tolist())
        selected_platforms = st.multiselect(
            "Platforms",
            options=available_platforms,
            default=available_platforms
        )

    with filter_col3:
        if "campaign_type" in df.columns:
            campaign_types = sorted(
                df["campaign_type"].dropna().unique().tolist()
            )
            selected_types = st.multiselect(
                "Campaign type",
                options=campaign_types,
                default=campaign_types
            )
        else:
            selected_types = []

# ---------------- APPLY FILTERS ----------------

filtered = df.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["date"].dt.date.between(start_date, end_date)
    ]

if selected_platforms:
    filtered = filtered[
        filtered["platform"].isin(selected_platforms)
    ]
else:
    filtered = filtered.iloc[0:0]

if "campaign_type" in filtered.columns and selected_types:
    filtered = filtered[
        filtered["campaign_type"].isin(selected_types)
    ]
elif "campaign_type" in filtered.columns and not selected_types:
    filtered = filtered.iloc[0:0]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

overall = metrics(filtered)

# ---------------- OVERVIEW PAGE ----------------

if page == "Overview":

    st.markdown("### Performance at a Glance")

    # 6 KPI cards with compact formatting for large numbers
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    k1.metric("Total Spend", money(overall["spend"], compact=True))
    k2.metric("Revenue", money(overall["revenue"], compact=True))
    k3.metric("ROAS", multiple(overall["roas"]))
    k4.metric("Cost / Purchase (CPA)", money(overall["cpa"]))
    k5.metric("Cost / Install (CPI)", money(overall["cpi"]))
    k6.metric("Conv. Rate (CVR)", percent(overall["conversion_rate"]))

    st.caption(
        f"Analyzing {len(filtered):,} records across "
        f"{filtered['campaign'].nunique():,} campaigns."
    )

    st.divider()

    left, right = st.columns([1.8, 1])

    # Daily trend visualization
    with left:
        st.markdown("### Daily Performance Trend")

        daily = (
            filtered.groupby("date", as_index=False)
            .agg(
                Revenue=("revenue", "sum"),
                Spend=("spend", "sum"),
                Purchases=("purchases", "sum"),
                Installs=("installs", "sum")
            )
            .sort_values("date")
        )

        metric_choice = st.selectbox(
            "Trend metric",
            ["Revenue", "Spend", "Purchases", "Installs"]
        )

        fig = px.line(
            daily,
            x="date",
            y=metric_choice,
            markers=False,
            color_discrete_sequence=[ACCENT]
        )

        style_chart(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Executive Readout
    with right:
        st.markdown("### ✦ Executive Readout")
        
        with st.container(border=True):
            st.markdown("<span class='badge-fact'>MEASURED FACT</span>", unsafe_allow_html=True)
            st.write(
                f"Selected records generate **{money(overall['revenue'])}** revenue from "
                f"**{money(overall['spend'])}** spend (ROAS: **{multiple(overall['roas'])}**, "
                f"Blended CPA: **{money(overall['cpa'])}**)."
            )

            platform_summary = (
                filtered.groupby("platform", as_index=False)
                .agg(
                    Spend=("spend", "sum"),
                    Installs=("installs", "sum"),
                    Purchases=("purchases", "sum"),
                    Revenue=("revenue", "sum")
                )
            )

            platform_summary["ROAS"] = platform_summary["Revenue"] / platform_summary["Spend"].replace(0, float("nan"))
            platform_summary["CPA"] = platform_summary["Spend"] / platform_summary["Purchases"].replace(0, float("nan"))
            
            comparable = platform_summary.dropna(subset=["ROAS"])

            if not comparable.empty:
                best = comparable.loc[comparable["ROAS"].idxmax()]
                st.write(
                    f"• **{best['platform']}** leads overall returns with **{best['ROAS']:.2f}x ROAS** "
                    f"and **{money(best['CPA'])} CPA**."
                )

            st.markdown("<span class='badge-hypo'>HYPOTHESIS TO TEST</span>", unsafe_allow_html=True)
            st.write(
                "A higher channel ROAS indicates strong last-touch correlation, but **does not prove incrementality**. "
                "Channel efficiency may be inflated by retargeting high-intent traffic that would have converted organically."
            )

            st.markdown("<span class='badge-action'>RECOMMENDED ACTION</span>", unsafe_allow_html=True)
            st.write(
                "Run a **geo-lift or intent-matched incrementality test** before scaling budgets to evaluate incremental Cost Per Acquisition (iCPA)."
            )

    st.divider()

    # Channel Comparison Section
    st.markdown("### Channel Intelligence: Google vs. Meta")

    plat_col1, plat_col2 = st.columns([1, 1])

    with plat_col1:
        p_agg = filtered.groupby("platform", as_index=False).agg(
            Spend=("spend", "sum"),
            Installs=("installs", "sum"),
            Purchases=("purchases", "sum"),
            Revenue=("revenue", "sum")
        )
        p_agg["CPI"] = p_agg["Spend"] / p_agg["Installs"].replace(0, float("nan"))
        p_agg["CPA"] = p_agg["Spend"] / p_agg["Purchases"].replace(0, float("nan"))
        p_agg["ROAS"] = p_agg["Revenue"] / p_agg["Spend"].replace(0, float("nan"))
        p_agg["CVR (%)"] = (p_agg["Purchases"] / p_agg["Installs"].replace(0, float("nan"))) * 100

        fig_plat = px.bar(
            p_agg,
            x="platform",
            y=["Spend", "Revenue"],
            barmode="group",
            color_discrete_sequence=[PURPLE, SECONDARY],
            title="Spend vs. Revenue by Platform"
        )
        style_chart(fig_plat)
        st.plotly_chart(fig_plat, use_container_width=True)

    with plat_col2:
        st.markdown("#### Multi-Metric Platform Breakdown")
        st.dataframe(
            p_agg.round(2),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Detailed efficiency comparison across primary platform networks.")

    st.markdown("### Top Performing Campaigns")

    top = (
        filtered.groupby(["campaign", "platform"], as_index=False)
        .agg(
            Spend=("spend", "sum"),
            Revenue=("revenue", "sum"),
            Installs=("installs", "sum"),
            Purchases=("purchases", "sum")
        )
    )

    top["CPI"] = top["Spend"] / top["Installs"].replace(0, float("nan"))
    top["CPA"] = top["Spend"] / top["Purchases"].replace(0, float("nan"))
    top["ROAS"] = top["Revenue"] / top["Spend"].replace(0, float("nan"))
    top["CVR (%)"] = (top["Purchases"] / top["Installs"].replace(0, float("nan"))) * 100

    top = top.sort_values("Revenue", ascending=False).head(10)

    st.dataframe(
        top.round(2),
        use_container_width=True,
        hide_index=True
    )

# ---------------- ADS PAGE ----------------

elif page == "Ads":
    st.markdown("### Channel & Ad Performance")

    summary = (
        filtered.groupby("platform", as_index=False)
        .agg(
            Spend=("spend", "sum"),
            Impressions=("impressions", "sum"),
            Clicks=("clicks", "sum"),
            Installs=("installs", "sum"),
            Purchases=("purchases", "sum"),
            Revenue=("revenue", "sum")
        )
    )

    summary["CPI"] = summary["Spend"] / summary["Installs"].replace(0, float("nan"))
    summary["CPA"] = summary["Spend"] / summary["Purchases"].replace(0, float("nan"))
    summary["ROAS"] = summary["Revenue"] / summary["Spend"].replace(0, float("nan"))
    summary["CVR (%)"] = (summary["Purchases"] / summary["Installs"].replace(0, float("nan"))) * 100

    st.dataframe(summary.round(2), use_container_width=True, hide_index=True)

    fig = px.bar(
        summary,
        x="platform",
        y="Spend",
        color="platform",
        color_discrete_sequence=[ACCENT, PURPLE],
        title="Spend Distribution by Platform"
    )
    style_chart(fig)
    st.plotly_chart(fig, use_container_width=True)

# ---------------- CAMPAIGNS PAGE ----------------

elif page == "Campaigns":
    st.markdown("### Campaign Explorer")

    table = (
        filtered.groupby(["campaign", "platform"], as_index=False)
        .agg(
            Spend=("spend", "sum"),
            Installs=("installs", "sum"),
            Purchases=("purchases", "sum"),
            Revenue=("revenue", "sum")
        )
    )

    table["CPI"] = table["Spend"] / table["Installs"].replace(0, float("nan"))
    table["CPA"] = table["Spend"] / table["Purchases"].replace(0, float("nan"))
    table["ROAS"] = table["Revenue"] / table["Spend"].replace(0, float("nan"))
    table["CVR (%)"] = (table["Purchases"] / table["Installs"].replace(0, float("nan"))) * 100

    sort_by = st.selectbox(
        "Rank campaigns by",
        ["Spend", "Revenue", "ROAS", "CPA", "CPI", "Purchases"]
    )

    ascending = sort_by in ["CPA", "CPI"]

    st.dataframe(
        table.sort_values(sort_by, ascending=ascending).round(2),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download campaign analysis",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="adpilot_campaign_analysis.csv",
        mime="text/csv"
    )

# ---------------- AUDIENCE PAGE ----------------

elif page == "Audience":
    st.markdown("### Market & Campaign Mix")

    if "market" in filtered.columns:
        market = (
            filtered.groupby("market", as_index=False)
            .agg(
                Spend=("spend", "sum"),
                Purchases=("purchases", "sum"),
                Revenue=("revenue", "sum")
            )
        )

        market["ROAS"] = market["Revenue"] / market["Spend"].replace(0, float("nan"))

        st.dataframe(
            market.round(2),
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            market,
            x="market",
            y="Revenue",
            color="market",
            title="Reported Revenue by Market"
        )
        style_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No market column exists in this dataset.")

    st.caption(
        "These are market-level summaries, not actual user-level "
        "audience or demographic insights."
    )

# ---------------- ATTRIBUTION PAGE ----------------

elif page == "Attribution":
    st.markdown("### Attribution & Measurement Intelligence")

    st.info(
        "This dashboard reports last-touch attributed figures supplied in the CSV. "
        "To assess true incremental performance, standard heuristic attribution model values should be paired "
        "with controlled incrementality testing (e.g., Geo-experiments or Matched Market Testing)."
    )

    attribution_summary = (
        filtered.groupby("platform", as_index=False)
        .agg(
            Spend=("spend", "sum"),
            Installs=("installs", "sum"),
            Purchases=("purchases", "sum"),
            Revenue=("revenue", "sum")
        )
    )

    attribution_summary["CPI"] = attribution_summary["Spend"] / attribution_summary["Installs"].replace(0, float("nan"))
    attribution_summary["CPA"] = attribution_summary["Spend"] / attribution_summary["Purchases"].replace(0, float("nan"))
    attribution_summary["ROAS"] = attribution_summary["Revenue"] / attribution_summary["Spend"].replace(0, float("nan"))

    st.dataframe(
        attribution_summary.round(2),
        use_container_width=True,
        hide_index=True
    )

# ---------------- REPORTS PAGE ----------------

elif page == "Reports":
    st.markdown("### Reports & Exports")

    st.write("Download the campaign records matching your active filters.")

    st.download_button(
        "Download filtered CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="adpilot_filtered_report.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.write("**Report summary**")

    report = pd.DataFrame(
        [
            {"Metric": "Records", "Value": len(filtered)},
            {"Metric": "Spend", "Value": round(overall["spend"], 2)},
            {"Metric": "Revenue", "Value": round(overall["revenue"], 2)},
            {"Metric": "Installs", "Value": overall["installs"]},
            {"Metric": "Purchases", "Value": overall["purchases"]},
            {"Metric": "CPI", "Value": round(overall["cpi"], 2) if overall["cpi"] else None},
            {"Metric": "CPA", "Value": round(overall["cpa"], 2) if overall["cpa"] else None},
            {"Metric": "ROAS", "Value": round(overall["roas"], 2) if overall["roas"] else None},
            {"Metric": "CVR (%)", "Value": round(overall["conversion_rate"], 2) if overall["conversion_rate"] else None}
        ]
    )

    st.dataframe(report, use_container_width=True, hide_index=True)

# ---------------- ALERTS PAGE ----------------

elif page == "Alerts":
    st.markdown("### Campaign Investigation Queue")

    table = (
        filtered.groupby(["campaign", "platform"], as_index=False)
        .agg(
            Spend=("spend", "sum"),
            Purchases=("purchases", "sum"),
            Revenue=("revenue", "sum")
        )
    )

    table["CPA"] = table["Spend"] / table["Purchases"].replace(0, float("nan"))
    table["ROAS"] = table["Revenue"] / table["Spend"].replace(0, float("nan"))

    table["Investigation reason"] = table.apply(
        lambda row: ", ".join(
            reason for condition, reason in [
                (row["Purchases"] == 0, "No purchases"),
                (
                    pd.notna(row["CPA"]) and row["CPA"] > TARGET_CPA,
                    "CPA above target"
                ),
                (
                    pd.notna(row["ROAS"]) and row["ROAS"] < TARGET_ROAS,
                    "ROAS below target"
                )
            ] if condition
        ),
        axis=1
    )

    alerts = table[table["Investigation reason"] != ""]

    st.caption(
        f"Illustrative thresholds: CPA > ₹{TARGET_CPA:.0f} "
        f"or ROAS < {TARGET_ROAS:.1f}x."
    )

    if alerts.empty:
        st.success("No campaigns match the current alert rules.")
    else:
        st.warning(f"{len(alerts)} campaign(s) flagged for investigation.")

        st.dataframe(
            alerts.sort_values("Spend", ascending=False).round(2),
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Alerts are investigation prompts, not proof of poor performance."
    )

# ---------------- SETTINGS PAGE ----------------

elif page == "Settings":
    st.markdown("### Workspace Settings")

    st.write("**Current thresholds**")
    st.write(f"Illustrative CPA target: ₹{TARGET_CPA:.2f}")
    st.write(f"Illustrative ROAS target: {TARGET_ROAS:.2f}x")

    st.write("**Data source**")
    st.code(str(CSV_FILE))

    st.write("**Dataset information**")
    st.write(f"Records loaded: {len(df):,}")
    st.write(f"Date range: {min_date} to {max_date}")
    st.write(f"Platforms: {', '.join(available_platforms)}")

    st.info(
        "The theme preference is retained during Streamlit session "
        "reruns. Persistent user preferences and editable thresholds "
        "will be added in a future version."
    )

# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "AdPilot AI · Performance Marketing Intelligence · "
    "Synthetic demo data · Recommendations require human review"
)