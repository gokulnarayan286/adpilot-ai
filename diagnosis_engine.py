
import pandas as pd
from pathlib import Path

# Find the project folder and load campaign data.
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "campaigns.csv"
OUTPUT_FILE = BASE_DIR / "diagnosis_results.csv"

df = pd.read_csv(INPUT_FILE)

# Convert numeric columns safely.
numeric_columns = [
    "spend", "impressions", "clicks",
    "installs", "purchases", "revenue"
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        ).fillna(0)

# Aggregate daily records into one row per campaign.
# campaign_id is the unique identifier.
group_columns = [
    "campaign_id", "campaign", "platform", "objective"
]

campaigns = (
    df.groupby(group_columns, as_index=False, dropna=False)[
        ["spend", "impressions", "clicks",
         "installs", "purchases", "revenue"]
    ].sum()
)

# Calculate metrics using totals, not averages of daily ratios.
campaigns["cpi"] = (
    campaigns["spend"] /
    campaigns["installs"].where(campaigns["installs"] != 0)
)

campaigns["purchase_cpa"] = (
    campaigns["spend"] /
    campaigns["purchases"].where(campaigns["purchases"] != 0)
)

campaigns["roas"] = (
    campaigns["revenue"] /
    campaigns["spend"].where(campaigns["spend"] != 0)
)

campaigns["diagnosis"] = "No major warning from these rules"
campaigns["priority"] = "Monitor"
campaigns["reason"] = "No rule-based warning was triggered"

# Compare each campaign only with campaigns that share
# its platform and objective.
for (platform, objective), group in campaigns.groupby(
    ["platform", "objective"]
):
    objective_name = str(objective).strip().lower()

    if objective_name == "app installs":
        valid = group[
            (group["installs"] > 0) & (group["spend"] > 0)
        ]

        if len(valid) < 4:
            campaigns.loc[valid.index, "reason"] = (
                "Too few comparable campaigns for a reliable "
                "relative benchmark"
            )
            continue

        high_cpi = valid["cpi"].quantile(0.75)

        flagged = valid[valid["cpi"] > high_cpi]

        for idx in flagged.index:
            campaigns.loc[idx, "diagnosis"] = "High CPI vs peers"
            campaigns.loc[idx, "priority"] = "Investigate"
            campaigns.loc[idx, "reason"] = (
                f"CPI is above the 75th percentile for "
                f"{platform} App Installs campaigns "
                f"(peer threshold: {high_cpi:.2f})"
            )

    elif objective_name == "purchases":
        valid = group[
            (group["spend"] > 0) &
            (group["purchases"] > 0)
        ]

        if len(valid) < 4:
            campaigns.loc[valid.index, "reason"] = (
                "Too few comparable campaigns for a reliable "
                "relative benchmark"
            )
            continue

        high_cpa = valid["purchase_cpa"].quantile(0.75)
        low_roas = valid["roas"].quantile(0.25)

        for idx in valid.index:
            expensive = campaigns.loc[idx, "purchase_cpa"] > high_cpa
            weak_roas = campaigns.loc[idx, "roas"] < low_roas

            if expensive or weak_roas:
                signals = []

                if expensive:
                    signals.append("purchase CPA above peer 75th percentile")

                if weak_roas:
                    signals.append("ROAS below peer 25th percentile")

                campaigns.loc[idx, "diagnosis"] = (
                    "Purchase efficiency warning"
                )
                campaigns.loc[idx, "priority"] = "Investigate"
                campaigns.loc[idx, "reason"] = "; ".join(signals)

    elif objective_name == "lead generation":
        # This dataset has no verified leads column.
        # Purchases are not a substitute for leads.
        campaigns.loc[group.index, "diagnosis"] = (
            "Lead efficiency cannot be assessed"
        )
        campaigns.loc[group.index, "priority"] = "Data needed"
        campaigns.loc[group.index, "reason"] = (
            "The dataset has no verified lead count. "
            "Add lead data before calculating cost per lead."
        )

# Save results for inspection and later dashboard integration.
campaigns = campaigns.sort_values(
    ["priority", "spend"],
    ascending=[True, False]
)

campaigns.to_csv(OUTPUT_FILE, index=False)

# Display a quick summary in the terminal.
print("\nADPILOT AI — CAMPAIGN DIAGNOSIS")
print("=" * 70)

print("\nDiagnosis counts:")
print(campaigns["diagnosis"].value_counts().to_string())

print("\nCampaigns requiring investigation or data:")
print(
    campaigns[
        campaigns["priority"].isin(["Investigate", "Data needed"])
    ][
        ["campaign_id", "campaign", "platform", "objective",
         "spend", "cpi", "purchase_cpa", "roas",
         "diagnosis", "reason"]
    ].round(2).to_string(index=False)
)

print(f"\nFull results saved to: {OUTPUT_FILE}")
print(f"Campaigns analysed: {len(campaigns)}")
