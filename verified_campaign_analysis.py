
import csv
import json
import os

from google import genai
from google.genai import types


# ==========================================
# CONFIGURATION
# ==========================================

CAMPAIGNS_FILE = "campaigns.csv"
OUTPUT_FILE = "verified_ai_recommendations.csv"

MODEL_NAME = "gemini-3.5-flash-lite"
MAX_CAMPAIGNS = 10

# Illustrative practice targets, not universal benchmarks.
CPI_TARGET = 10.0
CPA_TARGET = 100.0
ROAS_TARGET = 2.0


# ==========================================
# CSV HELPERS
# ==========================================

def load_campaigns(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def save_reports(path, reports):
    """Write a consistent report schema, including campaign IDs."""

    fieldnames = [
        "campaign_id",
        "campaign",
        "objective",
        "verified_metrics",
        "problem",
        "hypotheses",
        "experiments",
        "data_gaps",
        "confidence",
        "status",
    ]

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reports)


def safe_number(row, column):
    try:
        value = float(row.get(column, 0) or 0)
        return max(value, 0.0)
    except (ValueError, TypeError):
        return 0.0


# ==========================================
# OBJECTIVE CLASSIFICATION
# ==========================================

def classify_objective(objective):
    objective = objective.lower().replace("_", " ").strip()

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


# ==========================================
# PYTHON METRICS
# ==========================================

def calculate_metrics(row):
    spend = safe_number(row, "spend")
    impressions = safe_number(row, "impressions")
    clicks = safe_number(row, "clicks")
    installs = safe_number(row, "installs")
    purchases = safe_number(row, "purchases")
    revenue = safe_number(row, "revenue")

    return {
        "spend": round(spend, 2),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "installs": int(installs),
        "purchases": int(purchases),
        "revenue": round(revenue, 2),
        "ctr_percent": (
            round(clicks / impressions * 100, 2)
            if impressions else None
        ),
        "cpc": (
            round(spend / clicks, 2)
            if clicks else None
        ),
        "cpi": (
            round(spend / installs, 2)
            if installs else None
        ),
        "purchase_cpa": (
            round(spend / purchases, 2)
            if purchases else None
        ),
        "roas": (
            round(revenue / spend, 2)
            if spend else None
        ),
        "purchase_cvr_percent": (
            round(purchases / clicks * 100, 2)
            if clicks else None
        ),
    }


# ==========================================
# RULE-BASED INVESTIGATION
# ==========================================

def investigate_campaign(row, metrics):
    category = classify_objective(row.get("objective", ""))
    issues = []

    if metrics["spend"] == 0:
        return ["No recorded spend; performance cannot be assessed."]

    if category == "app_installs":
        cpi = metrics["cpi"]

        if cpi is None:
            issues.append("No installs recorded despite recorded spend.")
        elif cpi > CPI_TARGET:
            issues.append(
                f"CPI exceeds the illustrative target of INR {CPI_TARGET:.2f}."
            )

    elif category == "sales":
        cpa = metrics["purchase_cpa"]
        roas = metrics["roas"]

        if cpa is None:
            issues.append("No purchases recorded despite recorded spend.")
        elif cpa > CPA_TARGET:
            issues.append(
                f"Purchase CPA exceeds the illustrative target of "
                f"INR {CPA_TARGET:.2f}."
            )

        if roas is not None and roas < ROAS_TARGET:
            issues.append(
                f"ROAS is below the illustrative target of {ROAS_TARGET:.2f}x."
            )

    elif category == "lead_generation":
        issues.append(
            "Lead performance cannot be evaluated because verified "
            "lead counts are unavailable. Purchases are not leads."
        )

    else:
        issues.append(
            "Unknown campaign objective; clarify it before evaluation."
        )

    return issues


# ==========================================
# AI RESPONSE VALIDATION
# ==========================================

def validate_ai_response(result, category):
    required = [
        "problem",
        "hypotheses",
        "experiments",
        "data_gaps",
        "confidence",
    ]

    for field in required:
        if field not in result:
            raise ValueError(f"Missing response field: {field}")

    if not isinstance(result["problem"], str):
        raise ValueError("problem must be text.")

    for field in ["hypotheses", "experiments", "data_gaps"]:
        if not isinstance(result[field], list):
            raise ValueError(f"{field} must be a list.")

        if not all(isinstance(item, str) for item in result[field]):
            raise ValueError(f"All {field} items must be text.")

    if result["confidence"] not in ["low", "medium", "high"]:
        raise ValueError("Invalid confidence value.")

    if not result["hypotheses"]:
        raise ValueError("No hypotheses provided.")

    if not result["experiments"]:
        raise ValueError("No experiments provided.")

    all_text = " ".join(
        [result["problem"]]
        + result["hypotheses"]
        + result["experiments"]
        + result["data_gaps"]
    ).lower()

    if category != "lead_generation":
        irrelevant_phrases = [
            "lead performance cannot be evaluated",
            "cost per lead cannot be evaluated",
            "missing lead data",
        ]

        for phrase in irrelevant_phrases:
            if phrase in all_text:
                raise ValueError(
                    "Irrelevant lead-data statement for a non-lead campaign."
                )

    if category == "lead_generation":
        incorrect_claims = [
            "purchases are leads",
            "purchases count as leads",
            "purchases represent leads",
        ]

        for phrase in incorrect_claims:
            if phrase in all_text:
                raise ValueError(
                    "Purchases must not be treated as verified leads."
                )

    return result


# ==========================================
# GEMINI ANALYSIS
# ==========================================

def build_ai_report(client, row, metrics, issues):
    objective = row.get("objective", "Unknown")
    category = classify_objective(objective)

    instructions = {
        "app_installs": """
Focus on CPI, installs, CTR, CPC, and downstream quality when available.
Do not discuss cost per lead or missing lead data.
Do not assume purchases are the primary objective.
""",
        "sales": """
Focus on purchase CPA, ROAS, purchases, and revenue.
Do not discuss cost per lead or missing lead data.
""",
        "lead_generation": """
Verified lead counts are unavailable in this dataset.
Never treat purchases as leads.
State that cost per lead cannot be evaluated from the available data.
Do not make claims about lead efficiency.
""",
        "unknown": """
State that the objective needs clarification.
Avoid strong objective-specific conclusions.
""",
    }

    prompt = f"""
You are AdPilot AI, a careful performance marketing analyst.

CAMPAIGN ID:
{row.get("campaign_id", "Unknown")}

CAMPAIGN NAME:
{row.get("campaign", "Unknown")}

PLATFORM:
{row.get("platform", "Unknown")}

OBJECTIVE:
{objective}

OBJECTIVE CATEGORY:
{category}

VERIFIED METRICS CALCULATED BY PYTHON:
{json.dumps(metrics, indent=2)}

RULE-BASED FINDINGS:
{json.dumps(issues, indent=2)}

OBJECTIVE-SPECIFIC INSTRUCTIONS:
{instructions[category]}

RULES:
- Python calculated the metrics. Do not invent or alter numbers.
- Describe hypotheses as possibilities, not confirmed causes.
- Recommend practical experiments for human review.
- Mention only relevant data gaps.
- Never claim a test has run or a campaign has been changed.
- Confidence is qualitative, not a calibrated probability.
- Targets are illustrative, not universal benchmarks.
- Use plain text and standard notation; avoid unusual currency symbols.
- Do not recommend budget changes without sufficient evidence.

Return concise JSON matching the required schema.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "problem": {"type": "STRING"},
                    "hypotheses": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "experiments": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "data_gaps": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "confidence": {
                        "type": "STRING",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": [
                    "problem",
                    "hypotheses",
                    "experiments",
                    "data_gaps",
                    "confidence",
                ],
            },
        ),
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return validate_ai_response(json.loads(response.text), category)


# ==========================================
# MAIN PROGRAM
# ==========================================

def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Set it in your terminal."
        )

    campaigns = load_campaigns(CAMPAIGNS_FILE)

    if not campaigns:
        print("No campaigns found in campaigns.csv.")
        return

    # Ensure every source row has a unique ID.
    seen_ids = set()

    for row in campaigns:
        campaign_id = row.get("campaign_id", "").strip()

        if not campaign_id:
            raise ValueError("A campaign row has no campaign_id.")

        if campaign_id in seen_ids:
            raise ValueError(f"Duplicate campaign_id: {campaign_id}")

        seen_ids.add(campaign_id)

    candidates = []

    for row in campaigns:
        metrics = calculate_metrics(row)
        issues = investigate_campaign(row, metrics)

        if issues:
            candidates.append((row, metrics, issues))

    # This takes the first flagged rows, not necessarily the worst rows.
    selected = candidates[:MAX_CAMPAIGNS]

    if not selected:
        print("No campaigns were flagged by the current rules.")
        return

    client = genai.Client(api_key=api_key)
    reports = []

    for index, (row, metrics, issues) in enumerate(selected, start=1):
        campaign_id = row["campaign_id"]
        campaign_name = row.get("campaign", "Unknown")
        objective = row.get("objective", "Unknown")
        category = classify_objective(objective)

        print(
            f"\n[{index}/{len(selected)}] "
            f"{campaign_id} | {campaign_name}"
        )
        print(f"Objective: {objective} ({category})")

        try:
            result = build_ai_report(client, row, metrics, issues)

            report = {
                "campaign_id": campaign_id,
                "campaign": campaign_name,
                "objective": objective,
                "verified_metrics": json.dumps(metrics),
                "problem": result["problem"],
                "hypotheses": json.dumps(result["hypotheses"]),
                "experiments": json.dumps(result["experiments"]),
                "data_gaps": json.dumps(result["data_gaps"]),
                "confidence": result["confidence"],
                "status": "validated",
            }

            print(f"Problem: {result['problem']}")
            print(f"Confidence: {result['confidence']}")

        except Exception as error:
            print(f"Review required: {error}")

            report = {
                "campaign_id": campaign_id,
                "campaign": campaign_name,
                "objective": objective,
                "verified_metrics": json.dumps(metrics),
                "problem": "AI analysis failed validation or generation.",
                "hypotheses": json.dumps([]),
                "experiments": json.dumps([]),
                "data_gaps": json.dumps([
                    "Inspect the terminal error and retry if appropriate."
                ]),
                "confidence": "low",
                "status": "review_required",
            }

        reports.append(report)

    save_reports(OUTPUT_FILE, reports)

    validated = sum(
        report["status"] == "validated" for report in reports
    )
    needs_review = sum(
        report["status"] == "review_required" for report in reports
    )

    print("\n" + "=" * 45)
    print(f"Campaigns selected: {len(selected)}")
    print(f"Validated reports: {validated}")
    print(f"Reports needing review: {needs_review}")
    print(f"Output file: {OUTPUT_FILE}")
    print("Review recommendations before taking action.")


if __name__ == "__main__":
    main()
