
import csv
from pathlib import Path

# Example thresholds for learning.
TARGET_CPI = 10.0
TARGET_CPA = 100.0
TARGET_ROAS = 2.0
TARGET_COST_PER_LEAD = 150.0

MIN_INSTALLS_TO_SCALE = 50
MIN_PURCHASES_TO_SCALE = 10
MIN_LEAD_CONVERSIONS_TO_SCALE = 10

DATA_FILE = Path(__file__).parent / "campaigns.csv"
OUTPUT_FILE = Path(__file__).parent / "decision_results.csv"


def number(row, field):
    """Convert a CSV field to a number safely."""
    try:
        return float(row.get(field) or 0)
    except (ValueError, TypeError):
        return 0.0


def classify_objective(row):
    """Choose a campaign goal using the objective first."""
    objective = str(row.get("objective") or "").strip().lower()
    campaign_type = str(row.get("campaign_type") or "").strip().lower()

    # Give the explicit objective priority over campaign type.
    if "lead" in objective:
        return "LEADS"

    if any(word in objective for word in [
        "purchase", "sales", "shopping", "conversion", "roas"
    ]):
        return "PURCHASES"

    if any(word in objective for word in [
        "install", "app install"
    ]):
        return "INSTALLS"

    # Use campaign type only when the objective is inconclusive.
    if "lead" in campaign_type:
        return "LEADS"

    if any(word in campaign_type for word in [
        "purchase", "shopping", "sales"
    ]):
        return "PURCHASES"

    if any(word in campaign_type for word in [
        "install", "uac", "app"
    ]):
        return "INSTALLS"

    return "UNKNOWN"


def evaluate_campaign(row):
    """Evaluate one campaign and explain the recommendation."""

    name = row.get("campaign", "Unnamed campaign")
    platform = row.get("platform", "Unknown")
    objective = row.get("objective", "Unknown")

    spend = number(row, "spend")
    installs = number(row, "installs")
    purchases = number(row, "purchases")
    revenue = number(row, "revenue")

    goal = classify_objective(row)

    result = {
        "campaign": name,
        "platform": platform,
        "objective": objective,
        "metric": "Not determined",
        "metric_value": "",
        "conversion_data_note": "",
        "decision": "REVIEW OBJECTIVE",
        "reason": "The objective could not be classified.",
        "proposed_action": "Check the campaign objective and data."
    }

    if spend <= 0:
        result.update({
            "decision": "CHECK DATA",
            "reason": "Spend is zero, negative, or missing.",
            "proposed_action": "Verify campaign spend and source data."
        })
        return result

    # -----------------------------------------------
    # LEAD GENERATION
    # -----------------------------------------------
    if goal == "LEADS":
        result["metric"] = "Provisional cost per conversion"

        # IMPORTANT:
        # The CSV has no dedicated leads column.
        # Purchases is used only as a temporary conversion proxy.
        conversions = purchases

        result["conversion_data_note"] = (
            "Uses purchases as a provisional conversion proxy; "
            "not verified lead data."
        )

        if conversions <= 0:
            result.update({
                "decision": "INVESTIGATE",
                "reason": "No provisional conversions recorded.",
                "proposed_action": (
                    "Verify lead event tracking and identify the actual "
                    "lead conversion count before evaluating cost per lead."
                )
            })
            return result

        cost_per_conversion = spend / conversions
        result["metric_value"] = f"₹{cost_per_conversion:.2f}"

        if cost_per_conversion > TARGET_COST_PER_LEAD * 1.20:
            decision = "NEEDS ATTENTION"
            reason = (
                f"Provisional cost per conversion ₹{cost_per_conversion:.2f} "
                f"exceeds the review threshold of "
                f"₹{TARGET_COST_PER_LEAD * 1.20:.2f}."
            )
            action = (
                "Validate lead tracking and investigate audience, "
                "creative, landing page and lead quality."
            )

        elif (
            cost_per_conversion <= TARGET_COST_PER_LEAD
            and conversions >= MIN_LEAD_CONVERSIONS_TO_SCALE
        ):
            decision = "SCALE CANDIDATE"
            reason = (
                "Provisional cost per conversion meets the example target "
                "and conversion volume meets the example minimum."
            )
            action = (
                "Verify genuine lead counts and lead quality, then review "
                "business outcomes before considering a controlled test."
            )

        elif cost_per_conversion <= TARGET_COST_PER_LEAD:
            decision = "GATHER MORE DATA"
            reason = (
                "Provisional cost per conversion meets the example target, "
                "but conversion volume is low."
            )
            action = (
                "Validate conversion tracking and gather more data "
                "before considering scaling."
            )

        else:
            decision = "MONITOR"
            reason = (
                "Provisional cost per conversion is above target "
                "but below the review threshold."
            )
            action = "Monitor performance and validate lead quality."

    # -----------------------------------------------
    # APP INSTALLS
    # -----------------------------------------------
    elif goal == "INSTALLS":
        result["metric"] = "CPI"

        if installs <= 0:
            result.update({
                "decision": "INVESTIGATE",
                "reason": "No installs recorded.",
                "proposed_action": (
                    "Check install tracking, attribution and campaign setup."
                )
            })
            return result

        cpi = spend / installs
        result["metric_value"] = f"₹{cpi:.2f}"

        if cpi > TARGET_CPI * 1.20:
            decision = "NEEDS ATTENTION"
            reason = (
                f"CPI ₹{cpi:.2f} exceeds the review threshold "
                f"of ₹{TARGET_CPI * 1.20:.2f}."
            )
            action = (
                "Investigate creative, audience, attribution and "
                "downstream install quality."
            )

        elif cpi <= TARGET_CPI and installs >= MIN_INSTALLS_TO_SCALE:
            decision = "SCALE CANDIDATE"
            reason = "CPI meets target and install volume meets the minimum."
            action = (
                "Review retention and downstream conversions before "
                "considering a controlled scaling test."
            )

        elif cpi <= TARGET_CPI:
            decision = "GATHER MORE DATA"
            reason = "CPI meets target, but install volume is low."
            action = "Monitor volume and downstream install quality."

        else:
            decision = "MONITOR"
            reason = "CPI is above target but below the review threshold."
            action = "Monitor CPI trends and investigate efficiency."

    # -----------------------------------------------
    # PURCHASES / SALES
    # -----------------------------------------------
    elif goal == "PURCHASES":
        result["metric"] = "CPA and ROAS"

        if purchases <= 0:
            result.update({
                "decision": "INVESTIGATE",
                "reason": "No purchases recorded; CPA cannot be calculated.",
                "proposed_action": (
                    "Check purchase tracking, campaign objective "
                    "and conversion volume."
                )
            })
            return result

        cpa = spend / purchases
        roas = revenue / spend

        result["metric_value"] = (
            f"CPA ₹{cpa:.2f}; ROAS {roas:.2f}x"
        )

        if cpa > TARGET_CPA * 1.20 or roas < 1.0:
            decision = "NEEDS ATTENTION"
            reason = (
                f"CPA ₹{cpa:.2f}; ROAS {roas:.2f}x. "
                "At least one review threshold was breached."
            )
            action = (
                "Review tracking, margins, funnel performance and "
                "conversion quality before changing budgets."
            )

        elif (
            cpa <= TARGET_CPA
            and roas >= TARGET_ROAS
            and purchases >= MIN_PURCHASES_TO_SCALE
        ):
            decision = "SCALE CANDIDATE"
            reason = "CPA, ROAS and purchase volume meet example targets."
            action = (
                "Validate margins and performance trends before "
                "considering a controlled scaling test."
            )

        elif cpa <= TARGET_CPA and roas >= TARGET_ROAS:
            decision = "GATHER MORE DATA"
            reason = "CPA and ROAS meet targets, but purchase volume is low."
            action = "Gather more conversion data before considering scaling."

        else:
            decision = "MONITOR"
            reason = "The campaign does not qualify as a scale candidate."
            action = "Monitor CPA, ROAS and conversion trends."

    else:
        result.update({
            "decision": "REVIEW OBJECTIVE",
            "reason": (
                "No supported objective classification was found."
            ),
            "proposed_action": (
                "Inspect the objective and configure an appropriate metric."
            )
        })
        return result

    result["decision"] = decision
    result["reason"] = reason
    result["proposed_action"] = action

    return result


def main():
    if not DATA_FILE.exists():
        print(f"ERROR: File not found: {DATA_FILE}")
        return

    try:
        with open(
            DATA_FILE, "r", newline="", encoding="utf-8-sig"
        ) as file:
            campaigns = list(csv.DictReader(file))
    except OSError as error:
        print(f"ERROR reading campaign data: {error}")
        return

    if not campaigns:
        print("No campaign records found.")
        return

    results = [evaluate_campaign(row) for row in campaigns]

    fieldnames = [
        "campaign",
        "platform",
        "objective",
        "metric",
        "metric_value",
        "conversion_data_note",
        "decision",
        "reason",
        "proposed_action"
    ]

    try:
        with open(
            OUTPUT_FILE, "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    except OSError as error:
        print(f"ERROR saving results: {error}")
        return

    print("\n===== ADPILOT AI: DECISION ENGINE V2 =====")
    print(f"Campaigns evaluated: {len(results)}")

    for result in results:
        print("\n" + "-" * 55)
        print(f"Campaign: {result['campaign']}")
        print(f"Platform: {result['platform']}")
        print(f"Objective: {result['objective']}")
        print(f"Metric: {result['metric']}")
        print(f"Value: {result['metric_value'] or 'Unavailable'}")
        print(f"Decision: {result['decision']}")
        print(f"Reason: {result['reason']}")

        if result["conversion_data_note"]:
            print(f"Data note: {result['conversion_data_note']}")

        print(f"Proposed action: {result['proposed_action']}")

    print("\n===== DECISION SUMMARY =====")
    for decision in sorted({r["decision"] for r in results}):
        count = sum(1 for r in results if r["decision"] == decision)
        print(f"{decision}: {count}")

    print(f"\nResults saved to: {OUTPUT_FILE.name}")
    print("Recommendations require human review.")
    print("No live advertising budgets were changed.")


if __name__ == "__main__":
    main()
