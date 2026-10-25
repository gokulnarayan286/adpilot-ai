
import csv
import json
import re
from math import isclose

CAMPAIGNS_FILE = "campaigns.csv"
REPORTS_FILE = "ai_recommendations.csv"

# Allow small differences caused by rounding.
TOLERANCE = 0.02


def to_number(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def safe_divide(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def calculate_metrics(campaign):
    spend = to_number(campaign.get("spend"))
    impressions = to_number(campaign.get("impressions"))
    clicks = to_number(campaign.get("clicks"))
    installs = to_number(campaign.get("installs"))
    purchases = to_number(campaign.get("purchases"))
    revenue = to_number(campaign.get("revenue"))

    return {
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "installs": installs,
        "purchases": purchases,
        "revenue": revenue,
        "cpi": safe_divide(spend, installs),
        "purchase_cpa": safe_divide(spend, purchases),
        "roas": safe_divide(revenue, spend),
        "ctr_percent": safe_divide(clicks * 100, impressions),
    }


def load_campaigns():
    with open(
        CAMPAIGNS_FILE,
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        campaigns = {}

        for row in reader:
            campaigns[row["campaign"]] = row

        return campaigns


def load_reports():
    with open(
        REPORTS_FILE,
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


def extract_numeric_values(text):
    """
    Extract numbers from evidence text.

    Examples:
    'CPI is ₹76.34' -> [76.34]
    'ROAS reached 2.31x' -> [2.31]
    """

    pattern = r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?"
    matches = re.findall(pattern, text)

    values = []

    for match in matches:
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue

    return values


def verify_numeric_claims(evidence, metrics):
    """
    Check numeric evidence against known metrics.

    This is a conservative first version. It only checks
    evidence lines that explicitly name a recognized metric.
    """

    errors = []

    metric_patterns = {
        "cpi": r"\bCPI\b",
        "purchase_cpa": r"\b(?:purchase\s+)?CPA\b",
        "roas": r"\bROAS\b",
        "ctr_percent": r"\bCTR\b",
    }

    for statement in evidence:
        for metric_name, pattern in metric_patterns.items():
            if not re.search(pattern, statement, re.IGNORECASE):
                continue

            source_value = metrics[metric_name]

            if source_value is None:
                errors.append(
                    f"Cannot verify '{statement}': "
                    f"{metric_name} is unavailable in the source data."
                )
                continue

            claimed_values = extract_numeric_values(statement)

            if not claimed_values:
                continue

            # Use the final number in the statement as the claimed
            # metric value for this initial version.
            claimed_value = claimed_values[-1]

            if not isclose(
                claimed_value,
                round(source_value, 2),
                abs_tol=TOLERANCE,
            ):
                errors.append(
                    f"Possible numeric mismatch for {metric_name.upper()}: "
                    f"report says {claimed_value}, "
                    f"source calculates {source_value:.2f}. "
                    f"Evidence: {statement}"
                )

    return errors


def validate_report(report, campaign):
    errors = []

    if report.get("campaign") != campaign.get("campaign"):
        errors.append("Campaign name does not match source data.")

    try:
        evidence = json.loads(report.get("evidence", ""))
    except (json.JSONDecodeError, TypeError):
        return ["Evidence is not valid JSON."]

    if not isinstance(evidence, list):
        return ["Evidence must be a JSON list."]

    if not all(isinstance(item, str) for item in evidence):
        return ["Evidence contains a non-text item."]

    objective = campaign.get("objective", "").lower()

    if "lead" in objective:
        errors.append(
            "Lead performance requires human review: "
            "the source CSV has no verified leads column."
        )

    metrics = calculate_metrics(campaign)

    errors.extend(
        verify_numeric_claims(evidence, metrics)
    )

    return errors, metrics


def main():
    campaigns = load_campaigns()
    reports = load_reports()

    checked = 0
    flagged = 0

    for report in reports:
        campaign_name = report.get("campaign", "Unknown campaign")

        print(f"\nChecking: {campaign_name}")

        campaign = campaigns.get(campaign_name)

        if campaign is None:
            print("  REVIEW: Campaign not found in source CSV.")
            flagged += 1
            continue

        errors, metrics = validate_report(report, campaign)
        checked += 1

        print(
            "  Source metrics: "
            f"CPI={metrics['cpi']}, "
            f"Purchase CPA={metrics['purchase_cpa']}, "
            f"ROAS={metrics['roas']}, "
            f"CTR={metrics['ctr_percent']}"
        )

        if errors:
            flagged += 1

            for error in errors:
                print(f"  REVIEW: {error}")
        else:
            print("  Numeric evidence checks passed.")

    print("\n" + "=" * 50)
    print(f"Reports checked: {checked}")
    print(f"Reports flagged for review: {flagged}")
    print(
        "Reminder: automatic numeric checks are not a complete "
        "fact-check of natural-language claims."
    )


if __name__ == "__main__":
    main()
