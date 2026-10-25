
import csv
import json
import math

CAMPAIGNS_FILE = "campaigns.csv"
REPORTS_FILE = "verified_ai_recommendations.csv"


def load_csv(filename):
    with open(filename, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def safe_number(value):
    return float(value or 0)


campaigns = load_csv(CAMPAIGNS_FILE)
reports = load_csv(REPORTS_FILE)

# Campaign IDs must uniquely identify source rows.
source_by_id = {}

for campaign in campaigns:
    campaign_id = campaign["campaign_id"]

    if campaign_id in source_by_id:
        raise ValueError(f"Duplicate source campaign ID: {campaign_id}")

    source_by_id[campaign_id] = campaign

checked = 0
failed = 0

for report in reports:
    campaign_id = report["campaign_id"]

    if campaign_id not in source_by_id:
        print(f"FAIL | {campaign_id} | Not found in source data")
        failed += 1
        continue

    source = source_by_id[campaign_id]

    try:
        metrics = json.loads(report["verified_metrics"])

        # Recalculate these metrics from the original CSV.
        spend = safe_number(source["spend"])
        impressions = safe_number(source["impressions"])
        clicks = safe_number(source["clicks"])
        installs = safe_number(source["installs"])
        purchases = safe_number(source["purchases"])
        revenue = safe_number(source["revenue"])

        expected = {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "installs": installs,
            "purchases": purchases,
            "revenue": revenue,
            "CTR": clicks / impressions * 100 if impressions else 0,
            "CPC": spend / clicks if clicks else 0,
            "CPI": spend / installs if installs else 0,
            "CPA": spend / purchases if purchases else 0,
            "ROAS": revenue / spend if spend else 0,
        }

        # Metric names must match the keys in verified_metrics.
        # Only compare metrics that are present.
        mismatches = []

        for name, expected_value in expected.items():
            if name not in metrics:
                continue

            try:
                actual_value = float(metrics[name])
            except (TypeError, ValueError):
                mismatches.append(f"{name}: not numeric")
                continue

            if not math.isclose(
                actual_value,
                expected_value,
                rel_tol=0.02,
                abs_tol=0.02,
            ):
                mismatches.append(
                    f"{name}: report={actual_value:.2f}, "
                    f"source={expected_value:.2f}"
                )

        checked += 1

        if mismatches:
            failed += 1
            print(f"REVIEW | {campaign_id}")
            for mismatch in mismatches:
                print(f"  - {mismatch}")
        else:
            print(f"PASS | {campaign_id} | Reported metrics match checked source metrics")

    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
        failed += 1
        print(f"FAIL | {campaign_id} | {error}")

print("\n--- Validation Summary ---")
print(f"Reports checked: {checked}")
print(f"Reports requiring review: {failed}")
print(f"Reports without detected mismatches: {checked - failed}")
