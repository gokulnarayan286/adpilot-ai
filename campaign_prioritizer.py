
import csv
from pathlib import Path

from structured_investigator import calculate_metrics, screen_campaign

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "campaigns.csv"
OUTPUT_FILE = BASE_DIR / "prioritized_campaigns.csv"
MAX_CAMPAIGNS = 10


def score_campaign(row):
    metrics = calculate_metrics(row)
    screening = screen_campaign(row, metrics)

    score = 0
    reasons = []
    spend = metrics["spend"]
    goal = screening["goal"]

    if spend >= 10000:
        score += 20
        reasons.append("High spend")
    elif spend >= 5000:
        score += 10
        reasons.append("Moderate spend")

    if goal == "INSTALLS" and metrics["cpi"] is not None:
        if metrics["cpi"] > 12:
            score += 30
            reasons.append("Very high CPI")
        elif metrics["cpi"] > 10:
            score += 20
            reasons.append("Elevated CPI")

    if goal == "PURCHASES":
        cpa = metrics["purchase_cpa"]
        roas = metrics["roas"]

        if cpa is not None:
            if cpa > 120:
                score += 30
                reasons.append("Very high purchase CPA")
            elif cpa > 100:
                score += 20
                reasons.append("Elevated purchase CPA")

        if roas is not None:
            if roas < 1:
                score += 30
                reasons.append("Revenue below ad spend")
            elif roas < 2:
                score += 20
                reasons.append("ROAS below illustrative target")

    if spend > 0:
        if goal == "INSTALLS" and metrics["installs"] == 0:
            score += 25
            reasons.append("Spend with zero recorded installs")

        if goal == "PURCHASES" and metrics["purchases"] == 0:
            score += 25
            reasons.append("Spend with zero recorded purchases")

    if goal == "UNKNOWN":
        score += 10
        reasons.append("Unknown campaign objective")

    return {
        "campaign": row.get("campaign") or "Unnamed campaign",
        "platform": row.get("platform") or "Unknown",
        "objective": row.get("objective") or "Unknown",
        "spend": spend,
        "priority_score": score,
        "reasons": reasons,
    }


def main():
    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        print("No campaign rows found.")
        return

    ranked = [
        (row, score_campaign(row))
        for row in rows
    ]

    ranked.sort(
        key=lambda pair: (
            pair[1]["priority_score"],
            pair[1]["spend"],
        ),
        reverse=True,
    )

    top_campaigns = ranked[:MAX_CAMPAIGNS]

    fieldnames = list(rows[0].keys()) + [
        "priority_score",
        "priority_reasons",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for original_row, result in top_campaigns:
            output_row = dict(original_row)
            output_row["priority_score"] = result["priority_score"]
            output_row["priority_reasons"] = "; ".join(result["reasons"])
            writer.writerow(output_row)

    print("\nADPILOT AI — CAMPAIGN PRIORITIZATION")
    print(f"Campaigns evaluated: {len(rows)}")
    print(f"Campaigns selected: {len(top_campaigns)}")

    for rank, (original_row, result) in enumerate(top_campaigns, start=1):
        print(f"\n{rank}. {result['campaign']}")
        print(f"   Platform: {result['platform']}")
        print(f"   Spend: {result['spend']:.2f}")
        print(f"   Priority score: {result['priority_score']}")
        print("   Reasons: " + ", ".join(result["reasons"]))

    print(f"\nCSV saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
