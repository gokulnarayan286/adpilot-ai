
import csv
import json
import re
from math import isclose

CAMPAIGNS_FILE = "campaigns.csv"
REPORTS_FILE = "verified_ai_recommendations.csv"
TOLERANCE = 0.02


def number(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def divide(numerator, denominator):
    return numerator / denominator if denominator else None


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def calculate_source_metrics(campaign):
    spend = number(campaign.get("spend"))
    impressions = number(campaign.get("impressions"))
    clicks = number(campaign.get("clicks"))
    installs = number(campaign.get("installs"))
    purchases = number(campaign.get("purchases"))
    revenue = number(campaign.get("revenue"))

    return {
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "installs": installs,
        "purchases": purchases,
        "revenue": revenue,
        "ctr_percent": divide(clicks * 100, impressions),
        "cpc": divide(spend, clicks),
        "cpi": divide(spend, installs),
        "purchase_cpa": divide(spend, purchases),
        "roas": divide(revenue, spend),
        "purchase_cvr_percent": divide(purchases * 100, clicks),
    }


def parse_json_list(value, field, issues):
    try:
        result = json.loads(value or "[]")
    except (json.JSONDecodeError, TypeError):
        issues.append(f"{field} is not valid JSON.")
        return []

    if not isinstance(result, list):
        issues.append(f"{field} must be a JSON list.")
        return []

    if not all(isinstance(item, str) for item in result):
        issues.append(f"{field} contains a non-text item.")
        return []

    return result


def parse_verified_metrics(value, issues):
    try:
        result = json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        issues.append("verified_metrics is not valid JSON.")
        return None

    if not isinstance(result, dict):
        issues.append("verified_metrics must be a JSON object.")
        return None

    return result


def validate_metrics(reported, expected, issues):
    if reported is None:
        return

    # These are the metric names produced by the analysis script.
    for name, expected_value in expected.items():
        if name not in reported:
            issues.append(f"Missing metric field: {name}.")
            continue

        actual_value = reported[name]

        if expected_value is None:
            if actual_value is not None:
                issues.append(
                    f"{name}: source metric is unavailable, "
                    f"but report contains {actual_value!r}."
                )
            continue

        try:
            actual_value = float(actual_value)
        except (TypeError, ValueError):
            issues.append(f"{name} is not numeric.")
            continue

        if not isclose(
            actual_value,
            expected_value,
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE,
        ):
            issues.append(
                f"{name} mismatch: report={actual_value:.4f}, "
                f"source={expected_value:.4f}."
            )


def validate_objective(objective, hypotheses, experiments, data_gaps):
    issues = []
    objective_lower = objective.lower()

    analysis_text = " ".join(hypotheses + experiments).lower()
    gaps_text = " ".join(data_gaps).lower()

    if "lead" in objective_lower:
        # Only flag explicit numerical claims about lead performance.
        unsupported_patterns = [
            r"\b\d+(?:\.\d+)?\s+leads?\b",
            r"\b(?:generated|acquired|converted|recorded)"
            r"\s+\d+(?:\.\d+)?\s+leads?\b",
            r"\b(?:cost per lead|cpl)\s*(?:is|was|of|:|=)\s*"
            r"(?:₹|rs\.?\s*)?\d",
        ]

        for pattern in unsupported_patterns:
            if re.search(pattern, analysis_text):
                issues.append(
                    "Possible unsupported lead-performance claim. "
                    "Verify the claim against a trusted lead data source."
                )
                break

        # A missing-data note is valid. It is not automatically an error.
        mentions_leads = re.search(
            r"\b(?:lead|leads|cpl|cost per lead)\b",
            analysis_text,
            re.IGNORECASE,
        )

        documents_gap = re.search(
            r"\b(?:missing|unavailable|not available|lack of|absence of|"
            r"no verified|not provided|cannot verify|cannot measure)\b",
            gaps_text,
            re.IGNORECASE,
        )

        if mentions_leads and not documents_gap:
            issues.append(
                "Review lead-data availability: data_gaps does not "
                "clearly document whether lead data is verified."
            )

    elif any(
        term in objective_lower
        for term in ("app install", "app_installs", "install")
    ):
        # Mentioning leads only to explain a limitation can be legitimate.
        lead_terms = re.search(
            r"\b(?:cost per lead|cpl|lead generation)\b",
            analysis_text,
            re.IGNORECASE,
        )

        explicitly_about_missing_data = re.search(
            r"\b(?:missing|unavailable|not available|no verified)\b",
            analysis_text,
            re.IGNORECASE,
        )

        if lead_terms and not explicitly_about_missing_data:
            issues.append(
                "Possible objective mismatch: an app-install campaign "
                "contains lead-generation terminology."
            )

    return issues


def validate_report(report, source):
    issues = []
    campaign_id = report.get("campaign_id", "").strip()

    if report.get("campaign", "").strip() != source.get(
        "campaign", ""
    ).strip():
        issues.append("Campaign name does not match source data.")

    if report.get("objective", "").strip().lower() != source.get(
        "objective", ""
    ).strip().lower():
        issues.append("Objective does not match source data.")

    hypotheses = parse_json_list(
        report.get("hypotheses"), "hypotheses", issues
    )
    experiments = parse_json_list(
        report.get("experiments"), "experiments", issues
    )
    data_gaps = parse_json_list(
        report.get("data_gaps"), "data_gaps", issues
    )

    if not report.get("problem", "").strip():
        issues.append("Problem description is empty.")

    if not hypotheses:
        issues.append("No hypotheses supplied.")

    if not experiments:
        issues.append("No experiments supplied.")

    expected_metrics = calculate_source_metrics(source)
    reported_metrics = parse_verified_metrics(
        report.get("verified_metrics"), issues
    )

    validate_metrics(reported_metrics, expected_metrics, issues)

    issues.extend(
        validate_objective(
            report.get("objective", ""),
            hypotheses,
            experiments,
            data_gaps,
        )
    )

    return issues, expected_metrics


def main():
    campaigns = load_csv(CAMPAIGNS_FILE)
    reports = load_csv(REPORTS_FILE)

    source_by_id = {}

    for campaign in campaigns:
        campaign_id = campaign.get("campaign_id", "").strip()

        if not campaign_id:
            raise ValueError(
                "Source CSV contains a campaign without campaign_id."
            )

        if campaign_id in source_by_id:
            raise ValueError(
                f"Duplicate campaign_id in source CSV: {campaign_id}"
            )

        source_by_id[campaign_id] = campaign

    seen_report_ids = set()
    checked = 0
    flagged = 0

    print("AdPilot AI — Recommendation Validation")
    print("=" * 50)

    for report in reports:
        campaign_id = report.get("campaign_id", "").strip()
        campaign_name = report.get("campaign", "Unknown campaign")

        print(f"\nChecking {campaign_id} | {campaign_name}")

        if not campaign_id:
            print("  REVIEW: Report has no campaign ID.")
            flagged += 1
            continue

        if campaign_id in seen_report_ids:
            print("  REVIEW: Duplicate report campaign ID.")
            flagged += 1
            continue

        seen_report_ids.add(campaign_id)

        source = source_by_id.get(campaign_id)

        if source is None:
            print("  REVIEW: Campaign ID not found in source CSV.")
            flagged += 1
            continue

        checked += 1
        issues, metrics = validate_report(report, source)

        if issues:
            flagged += 1
            for issue in issues:
                print(f"  REVIEW: {issue}")
        else:
            print("  PASS: No issues detected by current checks.")

        print(
            "  Source metrics: "
            f"CPI={metrics['cpi']}, "
            f"Purchase CPA={metrics['purchase_cpa']}, "
            f"ROAS={metrics['roas']}"
        )

    print("\n" + "=" * 50)
    print(f"Reports checked: {checked}")
    print(f"Reports flagged: {flagged}")
    print(f"Reports without detected issues: {checked - flagged}")
    print(
        "\nNote: automated checks cannot prove every natural-language "
        "hypothesis or experiment is correct."
    )


if __name__ == "__main__":
    main()
