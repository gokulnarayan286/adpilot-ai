
import csv
import json

CAMPAIGNS_FILE = "campaigns.csv"
REPORTS_FILE = "verified_ai_recommendations.csv"


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def classify_objective(objective):
    """Classify a campaign using its stated objective."""

    objective = objective.lower()

    if "lead" in objective:
        return "lead_generation"

    if "install" in objective or "app" in objective:
        return "app_installs"

    if any(
        word in objective
        for word in ["purchase", "sales", "shopping", "conversion"]
    ):
        return "sales"

    return "unknown"


def validate_business_context(report, campaign):
    issues = []

    objective = campaign.get("objective", "")
    category = classify_objective(objective)

    try:
        hypotheses = json.loads(report.get("hypotheses", "[]"))
        experiments = json.loads(report.get("experiments", "[]"))
        data_gaps = json.loads(report.get("data_gaps", "[]"))
    except (json.JSONDecodeError, TypeError):
        return ["One or more AI list fields contain invalid JSON."]

    if not all(
        isinstance(items, list)
        for items in [hypotheses, experiments, data_gaps]
    ):
        return ["AI list fields must contain JSON lists."]

    all_text = " ".join(
        str(item)
        for items in [hypotheses, experiments, data_gaps]
        for item in items
    ).lower()

    # Lead-generation claims need actual lead data.
    if category != "lead_generation" and (
        "lead performance cannot be verified" in
        report.get("problem", "").lower()
    ):
        issues.append(
            "The AI describes missing lead data as a problem "
            "for a campaign that is not a lead-generation campaign."
        )

    # The source dataset does not contain a verified leads column.
    if category == "lead_generation":
        if "leads" not in campaign:
            issues.append(
                "Lead objective detected, but the source CSV "
                "does not contain a leads column."
            )

        if "purchase" in all_text and "lead" in all_text:
            issues.append(
                "Review whether the AI is incorrectly treating "
                "purchases as leads."
            )

    # Unknown objectives should not receive confident classifications.
    if category == "unknown":
        if report.get("confidence") == "high":
            issues.append(
                "High confidence is questionable because the "
                "campaign objective is not recognized."
            )

    # Ensure hypotheses are not empty.
    if not hypotheses:
        issues.append("No hypotheses were provided.")

    # Ensure experiments are not empty.
    if not experiments:
        issues.append("No experiments were provided.")

    return issues


def main():
    campaigns = load_csv(CAMPAIGNS_FILE)
    reports = load_csv(REPORTS_FILE)

    campaigns_by_name = {
        row["campaign"]: row for row in campaigns
    }

    checked = 0
    flagged = 0

    for report in reports:
        name = report.get("campaign", "Unknown campaign")

        print(f"\nChecking: {name}")

        campaign = campaigns_by_name.get(name)

        if campaign is None:
            print("  REVIEW: Campaign not found in source data.")
            flagged += 1
            continue

        issues = validate_business_context(report, campaign)
        checked += 1

        print(
            "  Objective category: "
            f"{classify_objective(campaign.get('objective', ''))}"
        )

        if issues:
            flagged += 1

            for issue in issues:
                print(f"  REVIEW: {issue}")
        else:
            print("  Business-context checks passed.")

    print("\n" + "=" * 45)
    print(f"Reports checked: {checked}")
    print(f"Reports flagged: {flagged}")
    print(
        "Passing these checks does not prove that every "
        "AI recommendation is correct."
    )


if __name__ == "__main__":
    main()
