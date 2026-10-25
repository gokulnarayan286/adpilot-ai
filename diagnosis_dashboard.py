
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "diagnosis_results.csv"

st.set_page_config(
    page_title="AdPilot AI — Diagnosis",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 AdPilot AI — Campaign Diagnosis")
st.caption("Rule-based campaign screening and investigation priorities")

st.info(
    "This dashboard uses mock data and relative peer benchmarks. "
    "A warning means investigate, not automatically pause or cut budget."
)

if not RESULTS_FILE.exists():
    st.error("diagnosis_results.csv was not found. Run diagnosis_engine.py first.")
    st.stop()

df = pd.read_csv(RESULTS_FILE)

required = {
    "campaign_id", "campaign", "platform", "objective",
    "spend", "diagnosis", "priority", "reason"
}

missing = required - set(df.columns)

if missing:
    st.error(f"Missing required columns: {', '.join(sorted(missing))}")
    st.stop()

# Ensure numeric metrics are usable.
for column in ["spend", "cpi", "purchase_cpa", "roas"]:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

# Sidebar filters
st.sidebar.header("Filters")

platforms = sorted(df["platform"].dropna().astype(str).unique())
selected_platforms = st.sidebar.multiselect(
    "Platform",
    platforms,
    default=platforms,
)

objectives = sorted(df["objective"].dropna().astype(str).unique())
selected_objectives = st.sidebar.multiselect(
    "Objective",
    objectives,
    default=objectives,
)

priorities = sorted(df["priority"].dropna().astype(str).unique())
selected_priorities = st.sidebar.multiselect(
    "Priority",
    priorities,
    default=priorities,
)

filtered = df[
    df["platform"].astype(str).isin(selected_platforms)
    & df["objective"].astype(str).isin(selected_objectives)
    & df["priority"].astype(str).isin(selected_priorities)
].copy()

# Summary metrics
total_campaigns = len(filtered)
investigate_count = (filtered["priority"] == "Investigate").sum()
data_needed_count = (filtered["priority"] == "Data needed").sum()
monitor_count = (filtered["priority"] == "Monitor").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Campaigns shown", f"{total_campaigns:,}")
c2.metric("Investigate", f"{investigate_count:,}")
c3.metric("Data needed", f"{data_needed_count:,}")
c4.metric("Monitor", f"{monitor_count:,}")

st.divider()

# Diagnosis distribution
st.subheader("Diagnosis Summary")

if filtered.empty:
    st.warning("No campaigns match your filters.")
else:
    summary = (
        filtered["diagnosis"]
        .value_counts()
        .rename_axis("Diagnosis")
        .reset_index(name="Campaign count")
    )
    st.bar_chart(summary.set_index("Diagnosis"))

# Campaign table
st.divider()
st.subheader("Campaign Investigation Queue")

table_columns = [
    column for column in [
        "campaign_id", "campaign", "platform", "objective",
        "spend", "cpi", "purchase_cpa", "roas",
        "priority", "diagnosis", "reason"
    ]
    if column in filtered.columns
]

st.dataframe(
    filtered[table_columns].round(2),
    use_container_width=True,
    hide_index=True,
)

# Detailed explanations
st.divider()
st.subheader("Why was a campaign flagged?")

if not filtered.empty:
    campaign_options = {
        f"{row.campaign_id} — {row.campaign}": row.campaign_id
        for row in filtered.itertuples()
    }

    selected_label = st.selectbox(
        "Select a campaign",
        list(campaign_options.keys()),
    )
    selected_id = campaign_options[selected_label]

    selected = filtered[
        filtered["campaign_id"].astype(str) == str(selected_id)
    ].iloc[0]

    st.markdown(f"**Diagnosis:** {selected['diagnosis']}")
    st.markdown(f"**Priority:** {selected['priority']}")
    st.markdown(f"**Evidence / reason:** {selected['reason']}")

    metric_columns = [
        ("Spend", "spend", "₹"),
        ("CPI", "cpi", "₹"),
        ("Purchase CPA", "purchase_cpa", "₹"),
        ("ROAS", "roas", ""),
    ]

    cols = st.columns(4)
    for col, (label, field, prefix) in zip(cols, metric_columns):
        if field in selected.index and pd.notna(selected[field]):
            value = selected[field]
            formatted = f"{prefix}{value:,.2f}"
            if field == "roas":
                formatted += "x"
            col.metric(label, formatted)
        else:
            col.metric(label, "N/A")

    if str(selected["objective"]).strip().lower() == "lead generation":
        st.warning(
            "Lead data is not verified in the source CSV. "
            "Do not interpret purchases as leads or calculate cost per lead."
        )

st.caption(
    "These are rule-based screening results on mock data. "
    "They do not prove causality or determine whether a campaign is profitable. "
    "Validate tracking, conversion volume, business targets, and context "
    "before making marketing decisions."
)
