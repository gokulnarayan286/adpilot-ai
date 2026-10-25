
import pandas as pd
import streamlit as st
from io import BytesIO

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="AdPilot AI | Marketing Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("🚀 AdPilot AI")
st.subheader("Marketing Campaign Analytics Dashboard")
st.write(
    "Upload your marketing data, map your columns, "
    "analyse campaign performance, and identify opportunities."
)

st.divider()


# --------------------------------------------------
# 2. HELPER FUNCTIONS
# --------------------------------------------------

def guess_column(columns, keywords):
    """Suggest a column based on its name."""
    for column in columns:
        column_name = str(column).lower().strip()

        if any(keyword in column_name for keyword in keywords):
            return column

    return "Not available"


def parse_numeric(series):
    """Convert common formatted numbers into numeric values."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace("%", "", regex=False)
        .replace({
            "": None,
            "nan": None,
            "None": None,
            "N/A": None,
            "null": None
        })
    )

    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def safe_divide(numerator, denominator):
    """Prevent division-by-zero errors."""
    if denominator == 0:
        return 0.0

    return numerator / denominator


def format_number(value):
    return f"{value:,.2f}"


# --------------------------------------------------
# 3. UPLOAD FILE
# --------------------------------------------------

st.header("1. Upload your marketing data")

uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Your file should contain campaign performance data."
)

if uploaded_file is None:
    st.info(
        "Upload a CSV or Excel file to get started. "
        "You can test the app with campaigns.csv."
    )

    st.markdown("### Recommended data columns")
    st.code(
        "campaign, platform, spend, impressions, clicks, "
        "installs, purchases, revenue",
        language="text"
    )

    st.stop()


# --------------------------------------------------
# 4. READ UPLOADED FILE
# --------------------------------------------------

try:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        raw_data = pd.read_csv(uploaded_file)
    else:
        raw_data = pd.read_excel(
            uploaded_file,
            engine="openpyxl"
        )

except Exception as error:
    st.error(f"Could not read this file: {error}")
    st.write(
        "Check that the file is valid and that Excel files "
        "are supported by your installed dependencies."
    )
    st.stop()


if raw_data.empty:
    st.error("The uploaded file contains no data.")
    st.stop()

if len(raw_data.columns) == 0:
    st.error("No columns were found in the uploaded file.")
    st.stop()

# Clean up column names.
raw_data.columns = [
    str(column).strip()
    for column in raw_data.columns
]

# Remove duplicate column names if any.
if raw_data.columns.duplicated().any():
    st.error(
        "Your file contains duplicate column names. "
        "Rename them before uploading."
    )
    st.stop()

st.success(
    f"File loaded successfully: {uploaded_file.name}"
)

st.write(
    f"**Rows:** {len(raw_data):,}  |  "
    f"**Columns:** {len(raw_data.columns):,}"
)

with st.expander("Preview uploaded data"):
    st.dataframe(
        raw_data.head(20),
        width="stretch",
        hide_index=True
    )

st.divider()


# --------------------------------------------------
# 5. COLUMN MAPPING
# --------------------------------------------------

st.header("2. Map your marketing columns")

st.write(
    "Select which uploaded columns represent each metric. "
    "Suggestions are automatic, but please verify them."
)

column_options = ["Not available"] + list(raw_data.columns)

mapping_columns = {
    "campaign": {
        "label": "Campaign name",
        "keywords": ["campaign_name", "campaign", "adset", "ad_set"]
    },
    "platform": {
        "label": "Platform / channel",
        "keywords": ["platform", "channel", "network", "source", "media"]
    },
    "spend": {
        "label": "Spend / cost",
        "keywords": ["spend", "cost", "amount_spent", "ad_spend", "budget_spent"]
    },
    "impressions": {
        "label": "Impressions",
        "keywords": ["impressions", "impression"]
    },
    "clicks": {
        "label": "Clicks",
        "keywords": ["clicks", "link_clicks", "click"]
    },
    "installs": {
        "label": "Installs",
        "keywords": ["installs", "app_installs", "install"]
    },
    "conversions": {
        "label": "Purchases / conversions",
        "keywords": ["purchases", "purchase", "conversions", "conversion", "orders", "results"]
    },
    "revenue": {
        "label": "Revenue",
        "keywords": ["revenue", "purchase_value", "conversion_value", "sales_value", "sales"]
    }
}

mapping = {}

with st.form("column_mapping_form"):
    left, right = st.columns(2)

    for index, (key, details) in enumerate(mapping_columns.items()):
        suggested = guess_column(
            raw_data.columns,
            details["keywords"]
        )

        default_index = (
            column_options.index(suggested)
            if suggested in column_options
            else 0
        )

        container = left if index % 2 == 0 else right

        with container:
            mapping[key] = st.selectbox(
                details["label"],
                options=column_options,
                index=default_index,
                key=f"mapping_{key}"
            )

    mapping_submitted = st.form_submit_button(
        "Apply column mapping",
        type="primary",
        width="stretch"
    )

if not mapping_submitted:
    st.info(
        "Verify the suggested mappings and click "
        "'Apply column mapping' to continue."
    )
    st.stop()


# --------------------------------------------------
# 6. CHOOSE MARKETING GOAL AND KPI
# --------------------------------------------------

st.header("3. Configure your analysis")

col1, col2, col3 = st.columns(3)

with col1:
    marketing_goal = st.selectbox(
        "Primary campaign goal",
        [
            "App Installs",
            "Purchases",
            "Lead Generation",
            "Traffic",
            "Other"
        ]
    )

with col2:
    primary_kpi = st.selectbox(
        "Primary KPI",
        [
            "Spend",
            "Impressions",
            "Clicks",
            "Installs",
            "Conversions",
            "Revenue",
            "CPC",
            "CPI",
            "CPA",
            "ROAS",
            "CTR"
        ]
    )

with col3:
    target_enabled = st.checkbox(
        "Compare KPI against a target"
    )

target_value = None

if target_enabled:
    target_value = st.number_input(
        f"Target value for {primary_kpi}",
        min_value=0.0,
        value=1.0,
        step=0.5
    )

    if primary_kpi in ["CPC", "CPI", "CPA"]:
        st.caption(
            "For cost KPIs, actual values at or below the target "
            "will be considered on target."
        )
    elif primary_kpi in ["ROAS", "CTR"]:
        st.caption(
            "For ROAS and CTR, actual values at or above "
            "the target will be considered on target."
        )

st.divider()


# --------------------------------------------------
# 7. NORMALIZE THE DATA
# --------------------------------------------------

analysis = pd.DataFrame(index=raw_data.index)

for key in [
    "spend",
    "impressions",
    "clicks",
    "installs",
    "conversions",
    "revenue"
]:
    source_column = mapping[key]

    if source_column != "Not available":
        analysis[key] = parse_numeric(
            raw_data[source_column]
        )
    else:
        analysis[key] = 0.0


if mapping["campaign"] != "Not available":
    analysis["campaign"] = (
        raw_data[mapping["campaign"]]
        .fillna("Unknown campaign")
        .astype(str)
        .str.strip()
    )
    analysis["campaign"] = analysis["campaign"].replace(
        "", "Unknown campaign"
    )
else:
    analysis["campaign"] = [
        f"Row {i + 1}"
        for i in range(len(raw_data))
    ]


if mapping["platform"] != "Not available":
    analysis["platform"] = (
        raw_data[mapping["platform"]]
        .fillna("Unknown platform")
        .astype(str)
        .str.strip()
    )
    analysis["platform"] = analysis["platform"].replace(
        "", "Unknown platform"
    )
else:
    analysis["platform"] = "All data"


# Identify which metrics actually exist in the uploaded file.
available_metrics = {
    key: mapping[key] != "Not available"
    for key in [
        "spend",
        "impressions",
        "clicks",
        "installs",
        "conversions",
        "revenue"
    ]
}

if not any(available_metrics.values()):
    st.error(
        "Map at least one numeric metric, such as Spend, "
        "Clicks, Installs, Conversions, or Revenue."
    )
    st.stop()


# --------------------------------------------------
# 8. CALCULATE METRICS
# --------------------------------------------------

total_spend = analysis["spend"].sum()
total_impressions = analysis["impressions"].sum()
total_clicks = analysis["clicks"].sum()
total_installs = analysis["installs"].sum()
total_conversions = analysis["conversions"].sum()
total_revenue = analysis["revenue"].sum()

cpc = safe_divide(total_spend, total_clicks)
cpi = safe_divide(total_spend, total_installs)
cpa = safe_divide(total_spend, total_conversions)
roas = safe_divide(total_revenue, total_spend)
ctr = safe_divide(total_clicks, total_impressions) * 100

analysis["CPC"] = (
    analysis["spend"] / analysis["clicks"].replace(0, float("nan"))
).fillna(0)

analysis["CPI"] = (
    analysis["spend"] / analysis["installs"].replace(0, float("nan"))
).fillna(0)

analysis["CPA"] = (
    analysis["spend"] / analysis["conversions"].replace(0, float("nan"))
).fillna(0)

analysis["ROAS"] = (
    analysis["revenue"] / analysis["spend"].replace(0, float("nan"))
).fillna(0)

analysis["CTR"] = (
    analysis["clicks"]
    / analysis["impressions"].replace(0, float("nan"))
    * 100
).fillna(0)


# --------------------------------------------------
# 9. KPI CARDS
# --------------------------------------------------

st.header("4. Performance overview")

kpi1, kpi2, kpi3 = st.columns(3)
kpi4, kpi5, kpi6 = st.columns(3)

kpi1.metric(
    "Total Spend",
    f"{total_spend:,.2f}" if available_metrics["spend"] else "N/A"
)

kpi2.metric(
    "Impressions",
    f"{total_impressions:,.0f}" if available_metrics["impressions"] else "N/A"
)

kpi3.metric(
    "Clicks",
    f"{total_clicks:,.0f}" if available_metrics["clicks"] else "N/A"
)

kpi4.metric(
    "Installs",
    f"{total_installs:,.0f}" if available_metrics["installs"] else "N/A"
)

kpi5.metric(
    "Conversions",
    f"{total_conversions:,.0f}" if available_metrics["conversions"] else "N/A"
)

kpi6.metric(
    "Revenue",
    f"{total_revenue:,.2f}" if available_metrics["revenue"] else "N/A"
)

st.subheader("Efficiency metrics")

eff1, eff2, eff3, eff4, eff5 = st.columns(5)

eff1.metric(
    "CPC",
    format_number(cpc) if available_metrics["spend"] and available_metrics["clicks"] else "N/A"
)

eff2.metric(
    "CPI",
    format_number(cpi) if available_metrics["spend"] and available_metrics["installs"] else "N/A"
)

eff3.metric(
    "CPA",
    format_number(cpa) if available_metrics["spend"] and available_metrics["conversions"] else "N/A"
)

eff4.metric(
    "ROAS",
    f"{roas:.2f}x" if available_metrics["revenue"] and available_metrics["spend"] else "N/A"
)

eff5.metric(
    "CTR",
    f"{ctr:.2f}%" if available_metrics["clicks"] and available_metrics["impressions"] else "N/A"
)

st.caption(
    "CPC = Spend / Clicks | CPI = Spend / Installs | "
    "CPA = Spend / Conversions | ROAS = Revenue / Spend | "
    "CTR = Clicks / Impressions. "
    "ROAS is displayed as a ratio, not a percentage."
)

st.divider()


# --------------------------------------------------
# 10. PRIMARY KPI AND TARGET
# --------------------------------------------------

st.header("5. Primary KPI analysis")

kpi_mapping = {
    "Spend": ("spend", total_spend),
    "Impressions": ("impressions", total_impressions),
    "Clicks": ("clicks", total_clicks),
    "Installs": ("installs", total_installs),
    "Conversions": ("conversions", total_conversions),
    "Revenue": ("revenue", total_revenue),
    "CPC": ("CPC", cpc),
    "CPI": ("CPI", cpi),
    "CPA": ("CPA", cpa),
    "ROAS": ("ROAS", roas),
    "CTR": ("CTR", ctr)
}

selected_column, selected_value = kpi_mapping[primary_kpi]

selected_metric_available = (
    available_metrics.get(selected_column, True)
)

if selected_column == "CPC":
    selected_metric_available = (
        available_metrics["spend"] and available_metrics["clicks"]
    )
elif selected_column == "CPI":
    selected_metric_available = (
        available_metrics["spend"] and available_metrics["installs"]
    )
elif selected_column == "CPA":
    selected_metric_available = (
        available_metrics["spend"] and available_metrics["conversions"]
    )
elif selected_column == "ROAS":
    selected_metric_available = (
        available_metrics["revenue"] and available_metrics["spend"]
    )
elif selected_column == "CTR":
    selected_metric_available = (
        available_metrics["clicks"] and available_metrics["impressions"]
    )

if not selected_metric_available:
    st.warning(
        f"The columns needed to calculate {primary_kpi} are not mapped. "
        "Update your column mapping to analyse this KPI."
    )
else:
    st.metric(
        f"Overall {primary_kpi}",
        f"{selected_value:,.2f}"
    )

    if target_enabled:
        if primary_kpi in ["CPC", "CPI", "CPA"]:
            target_met = selected_value <= target_value
        elif primary_kpi in ["ROAS", "CTR"]:
            target_met = selected_value >= target_value
        else:
            target_met = selected_value >= target_value

        if target_met:
            st.success(
                f"{primary_kpi} is meeting the configured target "
                f"of {target_value:,.2f}."
            )
        else:
            st.warning(
                f"{primary_kpi} is not meeting the configured target "
                f"of {target_value:,.2f}."
            )


# --------------------------------------------------
# 11. CAMPAIGN-LEVEL ANALYSIS
# --------------------------------------------------

st.divider()
st.header("6. Campaign performance")

campaign_metrics = (
    analysis.groupby(
        ["campaign", "platform"],
        as_index=False
    )
    .agg(
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        installs=("installs", "sum"),
        conversions=("conversions", "sum"),
        revenue=("revenue", "sum")
    )
)

campaign_metrics["CPC"] = (
    campaign_metrics["spend"]
    / campaign_metrics["clicks"].replace(0, float("nan"))
).fillna(0)

campaign_metrics["CPI"] = (
    campaign_metrics["spend"]
    / campaign_metrics["installs"].replace(0, float("nan"))
).fillna(0)

campaign_metrics["CPA"] = (
    campaign_metrics["spend"]
    / campaign_metrics["conversions"].replace(0, float("nan"))
).fillna(0)

campaign_metrics["ROAS"] = (
    campaign_metrics["revenue"]
    / campaign_metrics["spend"].replace(0, float("nan"))
).fillna(0)

campaign_metrics["CTR"] = (
    campaign_metrics["clicks"]
    / campaign_metrics["impressions"].replace(0, float("nan"))
    * 100
).fillna(0)


search_term = st.text_input(
    "Search campaign or platform",
    placeholder="For example: Meta or Prospecting"
)

filtered_campaigns = campaign_metrics.copy()

if search_term:
    matches = (
        filtered_campaigns["campaign"].str.contains(
            search_term,
            case=False,
            na=False,
            regex=False
        )
        | filtered_campaigns["platform"].str.contains(
            search_term,
            case=False,
            na=False,
            regex=False
        )
    )

    filtered_campaigns = filtered_campaigns[matches]

sort_options = [
    "Spend",
    "Impressions",
    "Clicks",
    "Installs",
    "Conversions",
    "Revenue",
    "CPC",
    "CPI",
    "CPA",
    "ROAS",
    "CTR"
]

sort_metric = st.selectbox(
    "Sort campaigns by",
    sort_options,
    index=0
)

ascending = st.checkbox(
    "Sort smallest to largest",
    value=False
)

filtered_campaigns = filtered_campaigns.sort_values(
    by=sort_metric.lower(),
    ascending=ascending
)

st.dataframe(
    filtered_campaigns.round(2),
    width="stretch",
    hide_index=True
)

st.caption(
    "Campaigns with identical campaign names on the same platform "
    "are combined in this view. For production use, map a unique "
    "campaign ID to keep similarly named campaigns separate."
)


# --------------------------------------------------
# 12. CAMPAIGN CHART
# --------------------------------------------------

st.divider()
st.header("7. Campaign comparison")

if not filtered_campaigns.empty:
    chart_metric = st.selectbox(
        "Choose metric for campaign chart",
        [
            "Spend",
            "Clicks",
            "Installs",
            "Conversions",
            "Revenue",
            "CPC",
            "CPI",
            "CPA",
            "ROAS",
            "CTR"
        ]
    )

    chart_data = filtered_campaigns[
        ["campaign", "platform", chart_metric.lower()]
    ].copy()

    chart_data["Campaign label"] = (
        chart_data["campaign"]
        + " ("
        + chart_data["platform"]
        + ")"
    )

    chart_data = chart_data.set_index("Campaign label")

    st.bar_chart(
        chart_data[chart_metric.lower()],
        width="stretch"
    )
else:
    st.info("No campaigns match your search.")


# --------------------------------------------------
# 13. PLATFORM COMPARISON
# --------------------------------------------------

st.divider()
st.header("8. Platform comparison")

platform_metrics = (
    analysis.groupby("platform", as_index=False)
    .agg(
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        installs=("installs", "sum"),
        conversions=("conversions", "sum"),
        revenue=("revenue", "sum")
    )
)

platform_metrics["CPC"] = (
    platform_metrics["spend"]
    / platform_metrics["clicks"].replace(0, float("nan"))
).fillna(0)

platform_metrics["CPI"] = (
    platform_metrics["spend"]
    / platform_metrics["installs"].replace(0, float("nan"))
).fillna(0)

platform_metrics["CPA"] = (
    platform_metrics["spend"]
    / platform_metrics["conversions"].replace(0, float("nan"))
).fillna(0)

platform_metrics["ROAS"] = (
    platform_metrics["revenue"]
    / platform_metrics["spend"].replace(0, float("nan"))
).fillna(0)

platform_metrics["CTR"] = (
    platform_metrics["clicks"]
    / platform_metrics["impressions"].replace(0, float("nan"))
    * 100
).fillna(0)

st.dataframe(
    platform_metrics.round(2),
    width="stretch",
    hide_index=True
)

platform_chart_metric = st.selectbox(
    "Choose platform comparison metric",
    [
        "Spend",
        "Clicks",
        "Installs",
        "Conversions",
        "Revenue",
        "CPC",
        "CPI",
        "CPA",
        "ROAS",
        "CTR"
    ],
    key="platform_chart_metric"
)

platform_chart = platform_metrics.set_index("platform")

st.bar_chart(
    platform_chart[platform_chart_metric.lower()],
    width="stretch"
)


# --------------------------------------------------
# 14. AUTOMATED OBSERVATIONS
# --------------------------------------------------

st.divider()
st.header("9. Automated observations")

observations = []

if available_metrics["spend"]:
    observations.append(
        f"Total mapped spend is {total_spend:,.2f}."
    )

if available_metrics["clicks"] and available_metrics["spend"]:
    observations.append(
        f"Overall CPC is {cpc:,.2f}."
    )

if available_metrics["installs"] and available_metrics["spend"]:
    observations.append(
        f"Overall CPI is {cpi:,.2f}."
    )

if available_metrics["conversions"] and available_metrics["spend"]:
    observations.append(
        f"Overall cost per mapped conversion is {cpa:,.2f}."
    )

if available_metrics["revenue"] and available_metrics["spend"]:
    observations.append(
        f"Overall ROAS is {roas:.2f}x."
    )

if available_metrics["clicks"] and available_metrics["impressions"]:
    observations.append(
        f"Overall CTR is {ctr:.2f}%."
    )

if available_metrics["spend"] and len(campaign_metrics) > 0:
    highest_spend = campaign_metrics.loc[
        campaign_metrics["spend"].idxmax()
    ]

    observations.append(
        f"Highest-spend campaign is '{highest_spend['campaign']}' "
        f"on {highest_spend['platform']}, with spend of "
        f"{highest_spend['spend']:,.2f}."
    )

if observations:
    for observation in observations:
        st.write(f"- {observation}")
else:
    st.info("Map numeric marketing columns to generate observations.")

if marketing_goal == "Lead Generation":
    st.warning(
        "Lead Generation selected: the conversions column must "
        "represent verified leads for CPL and lead efficiency "
        "analysis to be meaningful. Purchases must not be treated "
        "as leads."
    )

st.info(
    "These are descriptive observations, not causal conclusions. "
    "This version does not yet connect to Gemini, live ad accounts, "
    "or verified attribution data."
)


# --------------------------------------------------
# 15. DOWNLOAD RESULTS
# --------------------------------------------------

st.divider()
st.header("10. Export your results")

csv_data = filtered_campaigns.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download campaign analysis CSV",
    data=csv_data,
    file_name="adpilot_campaign_analysis.csv",
    mime="text/csv",
    width="stretch"
)

platform_csv = platform_metrics.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download platform analysis CSV",
    data=platform_csv,
    file_name="adpilot_platform_analysis.csv",
    mime="text/csv",
    width="stretch"
)

st.caption(
    "AdPilot AI — marketing analytics prototype. "
    "Always validate column mappings, currency, attribution windows, "
    "and conversion definitions before using results for budget decisions."
)
