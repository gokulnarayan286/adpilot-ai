
import csv
from pathlib import Path

# ADPILOT AI - LESSON 5
# Campaign Analytics using CSV data

CSV_FILE = Path(__file__).parent / "campaigns.csv"


def load_campaigns(file_path):
    campaigns = []

    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "campaign", "platform", "spend", "impressions",
            "clicks", "installs", "purchases", "revenue"
        }

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers.")

        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing CSV columns: {', '.join(sorted(missing))}"
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                campaign = {
                    "date": row["date"],
                    "campaign_id": row["campaign_id"],
                    "campaign": row["campaign"],
                    "platform": row["platform"],
                    "campaign_type": row["campaign_type"],
                    "market": row["market"],
                    "objective": row["objective"],
                    "spend": float(row["spend"]),
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "installs": int(row["installs"]),
                    "purchases": int(row["purchases"]),
                    "revenue": float(row["revenue"]),
                }
            except (ValueError, TypeError, KeyError):
                raise ValueError(
                    f"Invalid data on CSV row {row_number}."
                )

            if (
                campaign["spend"] < 0
                or campaign["impressions"] < 0
                or campaign["clicks"] < 0
                or campaign["installs"] < 0
                or campaign["purchases"] < 0
                or campaign["revenue"] < 0
            ):
                raise ValueError(
                    f"Negative metric on CSV row {row_number}."
                )

            campaigns.append(campaign)

    if not campaigns:
        raise ValueError("No campaign rows found.")

    return campaigns


def analyze_campaign(c):
    spend = c["spend"]
    impressions = c["impressions"]
    clicks = c["clicks"]
    installs = c["installs"]
    purchases = c["purchases"]
    revenue = c["revenue"]

    ctr = clicks / impressions * 100 if impressions else None
    cpc = spend / clicks if clicks else None
    cpi = spend / installs if installs else None
    cpa = spend / purchases if purchases else None
    roas = revenue / spend if spend else None
    cvr = purchases / clicks * 100 if clicks else None

    return {
        **c,
        "ctr": ctr,
        "cpc": cpc,
        "cpi": cpi,
        "cpa": cpa,
        "roas": roas,
        "cvr": cvr,
    }


def money(value):
    return f"₹{value:,.2f}" if value is not None else "N/A"


def percentage(value):
    return f"{value:.2f}%" if value is not None else "N/A"


def main():
    print("\n===== ADPILOT AI: CAMPAIGN ANALYTICS =====")

    campaigns = load_campaigns(CSV_FILE)
    results = [analyze_campaign(c) for c in campaigns]

    total_spend = sum(c["spend"] for c in results)
    total_impressions = sum(c["impressions"] for c in results)
    total_clicks = sum(c["clicks"] for c in results)
    total_installs = sum(c["installs"] for c in results)
    total_purchases = sum(c["purchases"] for c in results)
    total_revenue = sum(c["revenue"] for c in results)

    print(f"Campaign records: {len(results)}")
    print(f"Total spend: {money(total_spend)}")
    print(f"Total impressions: {total_impressions:,}")
    print(f"Total clicks: {total_clicks:,}")
    print(f"Total installs: {total_installs:,}")
    print(f"Total purchases: {total_purchases:,}")
    print(f"Total revenue: {money(total_revenue)}")

    print("\n===== OVERALL PERFORMANCE =====")
    print(
        "CTR:",
        percentage(total_clicks / total_impressions * 100)
        if total_impressions else "N/A"
    )
    print("CPC:", money(total_spend / total_clicks) if total_clicks else "N/A")
    print("CPI:", money(total_spend / total_installs) if total_installs else "N/A")
    print("CPA:", money(total_spend / total_purchases) if total_purchases else "N/A")
    print(
        "ROAS:",
        f"{total_revenue / total_spend:.2f}x"
        if total_spend else "N/A"
    )
    print(
        "Purchase CVR:",
        percentage(total_purchases / total_clicks * 100)
        if total_clicks else "N/A"
    )

    print("\n===== CAMPAIGN-LEVEL RESULTS =====")

    for c in results:
        print("\n" + "-" * 55)
        print(f'{c["campaign_id"]}: {c["campaign"]}')
        print(f'Platform: {c["platform"]} | Market: {c["market"]}')
        print(f'Objective: {c["objective"]}')
        print(f'Spend: {money(c["spend"])}')
        print(f'CTR: {percentage(c["ctr"])}')
        print(f'CPC: {money(c["cpc"])}')
        print(f'CPI: {money(c["cpi"])}')
        print(f'CPA: {money(c["cpa"])}')
        print(f'ROAS: {c["roas"]:.2f}x' if c["roas"] is not None else "ROAS: N/A")
        print(f'Purchase CVR: {percentage(c["cvr"])}')

    print("\n===== ANALYSIS COMPLETED =====")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print("\nCould not analyze campaign data.")
        print("Reason:", error)
