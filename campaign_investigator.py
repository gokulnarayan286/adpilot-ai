
import csv

CSV_FILE = "campaigns.csv"

TARGET_CPI = 10.0
TARGET_CPA = 100.0
TARGET_ROAS = 2.0


def number(row, field):
    try:
        return float(row.get(field, 0) or 0)
    except (ValueError, TypeError):
        return 0.0


def investigate_campaign(row):
    spend = number(row, "spend")
    impressions = number(row, "impressions")
    clicks = number(row, "clicks")
    installs = number(row, "installs")
    purchases = number(row, "purchases")
    revenue = number(row, "revenue")

    objective = row.get("objective", "").strip().lower()

    ctr = clicks / impressions * 100 if impressions else 0
    cpc = spend / clicks if clicks else 0
    cpi = spend / installs if installs else 0
    purchase_cpa = spend / purchases if purchases else 0
    roas = revenue / spend if spend else 0

    findings = []

    if spend <= 0:
        findings.append("Check spend data before evaluating performance.")

    elif "install" in objective:
        if installs <= 0:
            findings.append("Check install tracking: no installs recorded.")
        elif cpi > TARGET_CPI:
            findings.append(
                f"CPI is above the illustrative target of Rs {TARGET_CPI}."
            )
        else:
            findings.append("CPI is within the illustrative target.")

    elif any(word in objective for word in [
        "purchase", "sales", "shopping", "conversion"
    ]):
        if purchases <= 0:
            findings.append("No purchases recorded; check conversion tracking.")
        else:
            if purchase_cpa > TARGET_CPA:
                findings.append(
                    f"Purchase CPA is above the illustrative target "
                    f"of Rs {TARGET_CPA}."
                )

            if roas < TARGET_ROAS:
                findings.append(
                    f"ROAS is below the illustrative target of "
                    f"{TARGET_ROAS}x."
                )

            if purchase_cpa <= TARGET_CPA and roas >= TARGET_ROAS:
                findings.append(
                    "Purchase CPA and ROAS meet the illustrative targets."
                )

    elif "lead" in objective:
        findings.append(
            "Cannot evaluate cost per lead: campaigns.csv has no "
            "dedicated leads column. Purchases are not verified leads."
        )

    else:
        findings.append(
            "Unknown objective. Review the campaign goal before "
            "evaluating performance."
        )

    if clicks > 0 and installs == 0 and "install" in objective:
        findings.append(
            "Clicks exist but installs are zero; check the install funnel."
        )

    return {
        "campaign": row.get("campaign", "Unknown"),
        "platform": row.get("platform", "Unknown"),
        "objective": row.get("objective", "Unknown"),
        "spend": round(spend, 2),
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "cpi": round(cpi, 2),
        "purchase_cpa": round(purchase_cpa, 2),
        "roas": round(roas, 2),
        "findings": findings,
    }


def main():
    with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
        campaigns = list(csv.DictReader(file))

    if not campaigns:
        print("No campaign data found.")
        return

    print(f"Campaigns loaded: {len(campaigns)}")

    for row in campaigns[:10]:
        result = investigate_campaign(row)

        print("\n" + "=" * 50)
        print("CAMPAIGN:", result["campaign"])
        print("PLATFORM:", result["platform"])
        print("OBJECTIVE:", result["objective"])
        print("SPEND: Rs", result["spend"])
        print("CTR:", result["ctr"], "%")
        print("CPC: Rs", result["cpc"])
        print("CPI: Rs", result["cpi"])
        print("Purchase CPA: Rs", result["purchase_cpa"])
        print("ROAS:", result["roas"], "x")
        print("FINDINGS:")

        for finding in result["findings"]:
            print("-", finding)


if __name__ == "__main__":
    main()
