
# AdPilot AI - Version 5.0
# Platform Analysis & Budget Recommendations

import csv
from collections import defaultdict

CSV_FILE = "campaigns.csv"

TARGET_CPA = 80.0
TARGET_ROAS = 2.0

# Store totals for each platform and campaign
platforms = defaultdict(lambda: {
    "spend": 0.0,
    "impressions": 0,
    "clicks": 0,
    "installs": 0,
    "purchases": 0,
    "revenue": 0.0,
    "records": 0
})

campaigns = defaultdict(lambda: {
    "platform": "",
    "spend": 0.0,
    "installs": 0,
    "purchases": 0,
    "revenue": 0.0,
    "records": 0
})

# Read CSV data
with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    required_columns = {
        "campaign", "platform", "spend",
        "installs", "purchases", "revenue"
    }

    if not required_columns.issubset(reader.fieldnames or []):
        raise ValueError(
            "CSV is missing one or more required columns."
        )

    for row in reader:
        platform = row["platform"].strip()
        name = row["campaign"].strip()

        if not platform or not name:
            continue

        spend = float(row["spend"])
        installs = int(row["installs"])
        purchases = int(row["purchases"])
        revenue = float(row["revenue"])

        impressions = int(row.get("impressions") or 0)
        clicks = int(row.get("clicks") or 0)

        if spend < 0 or installs < 0 or purchases < 0 or revenue < 0:
            raise ValueError("Negative values found in campaign data.")

        # Aggregate platform performance
        p = platforms[platform]
        p["spend"] += spend
        p["impressions"] += impressions
        p["clicks"] += clicks
        p["installs"] += installs
        p["purchases"] += purchases
        p["revenue"] += revenue
        p["records"] += 1

        # Aggregate campaigns with the same name
        key = (platform, name)
        c = campaigns[key]
        c["platform"] = platform
        c["spend"] += spend
        c["installs"] += installs
        c["purchases"] += purchases
        c["revenue"] += revenue
        c["records"] += 1


def calculate_metrics(data):
    spend = data["spend"]
    installs = data["installs"]
    purchases = data["purchases"]
    revenue = data["revenue"]

    return {
        "cpi": spend / installs if installs else None,
        "cpa": spend / purchases if purchases else None,
        "roas": revenue / spend if spend else None,
        "conversion_rate": (
            purchases / installs * 100 if installs else None
        )
    }


def money(value):
    if value is None:
        return "N/A"
    return f"₹{value:,.2f}"


def ratio(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


# 1. Platform-level report
print("\n" + "=" * 60)
print("           ADPILOT AI - PLATFORM REPORT")
print("=" * 60)

for platform, data in sorted(platforms.items()):
    m = calculate_metrics(data)

    print(f"\nPlatform: {platform}")
    print(f"Records: {data['records']}")
    print(f"Spend: {money(data['spend'])}")
    print(f"Installs: {data['installs']:,}")
    print(f"Purchases: {data['purchases']:,}")
    print(f"Revenue: {money(data['revenue'])}")
    print(f"CPI: {money(m['cpi'])}")
    print(f"CPA: {money(m['cpa'])}")
    print(f"ROAS: {ratio(m['roas'])}")

    if m["cpa"] is None:
        print("Alert: No purchases recorded.")
    elif m["cpa"] > TARGET_CPA:
        print("Alert: Aggregate CPA is above target.")
    else:
        print("Status: Aggregate CPA is within target.")

    if m["roas"] is not None and m["roas"] < TARGET_ROAS:
        print("Alert: Aggregate ROAS is below target.")


# 2. Rank aggregated campaigns
rankable = []

for (platform, name), data in campaigns.items():
    metrics = calculate_metrics(data)

    rankable.append({
        "platform": platform,
        "name": name,
        "spend": data["spend"],
        "installs": data["installs"],
        "purchases": data["purchases"],
        "revenue": data["revenue"],
        "cpa": metrics["cpa"],
        "roas": metrics["roas"]
    })

print("\n" + "=" * 60)
print("           TOP 5 CAMPAIGNS BY ROAS")
print("=" * 60)

# Exclude campaigns with less than 10 purchases to reduce
# misleading rankings from very small purchase volumes.
eligible = [
    c for c in rankable
    if c["purchases"] >= 10 and c["roas"] is not None
]

top_campaigns = sorted(
    eligible,
    key=lambda c: c["roas"],
    reverse=True
)[:5]

if not top_campaigns:
    print("Not enough eligible campaigns to rank.")
else:
    for position, c in enumerate(top_campaigns, start=1):
        print(
            f"{position}. {c['name']} ({c['platform']})"
            f" | ROAS: {ratio(c['roas'])}"
            f" | CPA: {money(c['cpa'])}"
            f" | Purchases: {c['purchases']}"
        )


# 3. Campaigns needing investigation
print("\n" + "=" * 60)
print("        CAMPAIGNS NEEDING INVESTIGATION")
print("=" * 60)

flagged = []

for c in rankable:
    reasons = []

    if c["purchases"] == 0:
        reasons.append("No purchases")

    elif c["cpa"] is not None and c["cpa"] > TARGET_CPA:
        reasons.append("CPA above target")

    if c["roas"] is not None and c["roas"] < TARGET_ROAS:
        reasons.append("ROAS below target")

    if reasons:
        flagged.append((c, reasons))

flagged.sort(key=lambda item: item[0]["spend"], reverse=True)

if not flagged:
    print("No campaigns flagged by the current rules.")
else:
    for c, reasons in flagged[:10]:
        print(
            f"- {c['name']} ({c['platform']})"
            f" | Spend: {money(c['spend'])}"
            f" | CPA: {money(c['cpa'])}"
            f" | ROAS: {ratio(c['roas'])}"
        )
        print("  Reasons:", ", ".join(reasons))


# 4. Budget investigation recommendations
print("\n" + "=" * 60)
print("       BUDGET INVESTIGATION RECOMMENDATIONS")
print("=" * 60)

if len(platforms) < 2:
    print("Add at least two platforms to compare performance.")
else:
    platform_metrics = {
        name: calculate_metrics(data)
        for name, data in platforms.items()
    }

    for name, data in sorted(platforms.items()):
        m = platform_metrics[name]

        print(f"\n{name}:")

        if data["purchases"] < 30:
            print(
                "Recommendation: Gather more conversion data "
                "before considering a budget change."
            )
        elif m["cpa"] is not None and m["roas"] is not None:
            if m["cpa"] <= TARGET_CPA and m["roas"] >= TARGET_ROAS:
                print(
                    "Recommendation: Investigate whether this "
                    "platform can absorb more budget efficiently."
                )
            else:
                print(
                    "Recommendation: Investigate costs, revenue, "
                    "tracking and campaign mix before reallocating."
                )
        else:
            print(
                "Recommendation: Validate data before making "
                "a budget decision."
            )

print("\nAnalysis complete.")
print("Note: All recommendations are based on configured rules.")
print("Validate attribution, margins and incrementality before")
print("making actual budget changes.")
