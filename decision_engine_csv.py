
import csv
from pathlib import Path

# Learning thresholds — change these as needed.
TARGET_CPA = 100.0
MIN_PURCHASES_TO_SCALE = 10
POOR_CPA_MULTIPLIER = 1.20

CSV_FILE = Path(__file__).parent / "campaigns.csv"


def load_campaigns():
    """Read campaign records from our existing CSV file."""
    with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def evaluate_campaign(campaign):
    """Evaluate one campaign and return a decision with its reasoning."""

    name = campaign.get("campaign", "Unnamed campaign")
    platform = campaign.get("platform", "Unknown")
    objective = campaign.get("objective", "Unknown")

    spend = float(campaign.get("spend") or 0)
    purchases = int(float(campaign.get("purchases") or 0))
    revenue = float(campaign.get("revenue") or 0)

    # Do not use purchase CPA rules for campaigns with no spend.
    if spend <= 0:
        return {
            "campaign": name,
            "platform": platform,
            "decision": "CHECK DATA",
            "reason": "Spend is zero or missing. Verify the campaign data.",
            "proposed_action": "Check spend and tracking data."
        }

    # We need purchase data before evaluating purchase CPA.
    if purchases <= 0:
        return {
            "campaign": name,
            "platform": platform,
            "decision": "INVESTIGATE",
            "reason": "No purchases recorded; CPA cannot be calculated.",
            "proposed_action": (
                "Check the campaign objective, conversion tracking, "
                "spend and conversion volume."
            )
        }

    cpa = spend / purchases
    roas = revenue / spend

    # Rule 1: CPA is too high relative to our target.
    if cpa > TARGET_CPA * POOR_CPA_MULTIPLIER:
        decision = "NEEDS ATTENTION"
        reason = (
            f"CPA ₹{cpa:.2f} is above the review threshold "
            f"of ₹{TARGET_CPA * POOR_CPA_MULTIPLIER:.2f}."
        )
        action = (
            "Investigate audience, creative, funnel and conversion "
            "quality before considering budget changes."
        )

    # Rule 2: CPA is good, but we need enough purchase volume.
    elif cpa <= TARGET_CPA and purchases >= MIN_PURCHASES_TO_SCALE:
        decision = "SCALE CANDIDATE"
        reason = (
            f"CPA ₹{cpa:.2f} is within target and there are "
            f"{purchases} purchases."
        )
        action = (
            "Review conversion quality, ROAS, margins and recent trends; "
            "consider a controlled scaling test if the evidence supports it."
        )

    # Rule 3: CPA looks good, but purchase volume is low.
    elif cpa <= TARGET_CPA:
        decision = "GATHER MORE DATA"
        reason = (
            f"CPA ₹{cpa:.2f} is within target, but only "
            f"{purchases} purchases are recorded."
        )
        action = "Continue monitoring and gather more conversion data."

    # Rule 4: CPA is above target but not above the review threshold.
    else:
        decision = "MONITOR"
        reason = (
            f"CPA ₹{cpa:.2f} is above target ₹{TARGET_CPA:.2f}, "
            "but not above the review threshold."
        )
        action = "Monitor performance and inspect trends before acting."

    return {
        "campaign": name,
        "platform": platform,
        "objective": objective,
        "spend": spend,
        "purchases": purchases,
        "cpa": cpa,
        "roas": roas,
        "decision": decision,
        "reason": reason,
        "proposed_action": action
    }


def main():
    campaigns = load_campaigns()

    if not campaigns:
        print("No campaign records found in campaigns.csv.")
        return

    print("\n===== ADPILOT AI: DECISION ENGINE =====")
    print(f"Target CPA: ₹{TARGET_CPA:.2f}")
    print(f"Minimum purchases to consider scaling: {MIN_PURCHASES_TO_SCALE}")
    print("-" * 65)

    results = [evaluate_campaign(campaign) for campaign in campaigns]

    for result in results:
        print(f"\nCampaign: {result['campaign']}")
        print(f"Platform: {result['platform']}")
        print(f"Decision: {result['decision']}")

        if "cpa" in result:
            print(f"CPA: ₹{result['cpa']:.2f}")
            print(f"ROAS: {result['roas']:.2f}x")

        print(f"Reason: {result['reason']}")
        print(f"Proposed action: {result['proposed_action']}")
        print("-" * 65)

    print("\n===== DECISION SUMMARY =====")
    for decision in sorted({r["decision"] for r in results}):
        count = sum(1 for r in results if r["decision"] == decision)
        print(f"{decision}: {count} campaign(s)")

    print("\nThese are recommendations for human review.")
    print("AdPilot AI does not change live advertising budgets.")


if __name__ == "__main__":
    main()
