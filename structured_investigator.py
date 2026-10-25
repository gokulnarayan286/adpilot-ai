
import csv
import json
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types


# ==================================================
# 1. CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "campaigns.csv"
OUTPUT_FILE = BASE_DIR / "ai_recommendations.csv"

MODEL_NAME = "gemini-3.5-flash-lite"

# Illustrative practice thresholds, not approved business targets.
TARGET_CPI = 10.0
TARGET_CPA = 100.0
TARGET_ROAS = 2.0

MAX_CAMPAIGNS = 10


# ==================================================
# 2. GEMINI CLIENT
# ==================================================

def get_gemini_client():
    """Initialize Gemini only when an AI request is needed."""

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Configure it in your "
            "terminal before running Gemini investigations."
        )

    return genai.Client()


# ==================================================
# 3. STRUCTURED REPORT SCHEMA
# ==================================================

REPORT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "campaign": {"type": "STRING"},
        "problem": {"type": "STRING"},
        "evidence": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
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
        "campaign",
        "problem",
        "evidence",
        "hypotheses",
        "experiments",
        "data_gaps",
        "confidence",
    ],
}

REQUIRED_FIELDS = [
    "campaign",
    "problem",
    "evidence",
    "hypotheses",
    "experiments",
    "data_gaps",
    "confidence",
]

LIST_FIELDS = [
    "evidence",
    "hypotheses",
    "experiments",
    "data_gaps",
]

VALID_CONFIDENCE = {"low", "medium", "high"}


# ==================================================
# 4. DATA CONVERSION AND METRICS
# ==================================================

def number(value):
    """Convert a value to a non-negative number."""

    try:
        result = float(value or 0)
        return result if result >= 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


def ratio(numerator, denominator):
    """Return None when the denominator is zero."""

    if denominator == 0:
        return None
    return numerator / denominator


def format_metric(value, suffix=""):
    """Format a metric without treating missing data as zero."""

    if value is None:
        return "unavailable"
    return f"{value:.2f}{suffix}"


def calculate_metrics(row):
    """Calculate performance metrics for one campaign."""

    spend = number(row.get("spend"))
    impressions = number(row.get("impressions"))
    clicks = number(row.get("clicks"))
    installs = number(row.get("installs"))
    purchases = number(row.get("purchases"))
    revenue = number(row.get("revenue"))

    ctr = ratio(clicks * 100, impressions)
    cpc = ratio(spend, clicks)
    cpi = ratio(spend, installs)
    purchase_cpa = ratio(spend, purchases)
    roas = ratio(revenue, spend)
    purchase_cvr = ratio(purchases * 100, installs)

    return {
        "spend": round(spend, 2),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "installs": int(installs),
        "purchases": int(purchases),
        "revenue": round(revenue, 2),
        "ctr_percent": round(ctr, 2) if ctr is not None else None,
        "cpc": round(cpc, 2) if cpc is not None else None,
        "cpi": round(cpi, 2) if cpi is not None else None,
        "purchase_cpa": (
            round(purchase_cpa, 2)
            if purchase_cpa is not None else None
        ),
        "roas": round(roas, 2) if roas is not None else None,
        "purchase_cvr_percent": (
            round(purchase_cvr, 2)
            if purchase_cvr is not None else None
        ),
    }


# ==================================================
# 5. OBJECTIVE CLASSIFICATION
# ==================================================

def classify_objective(row):
    """Infer the campaign goal from available fields."""

    objective = str(row.get("objective") or "").strip().lower()
    campaign_type = (
        str(row.get("campaign_type") or "").strip().lower()
    )

    if "lead" in objective:
        return "LEADS"

    if any(word in objective for word in (
        "purchase", "sales", "shopping", "conversion", "roas"
    )):
        return "PURCHASES"

    if "install" in objective:
        return "INSTALLS"

    if "lead" in campaign_type:
        return "LEADS"

    if any(word in campaign_type for word in (
        "purchase", "shopping", "sales"
    )):
        return "PURCHASES"

    if any(word in campaign_type for word in (
        "install", "uac", "app"
    )):
        return "INSTALLS"

    return "UNKNOWN"


# ==================================================
# 6. RULE-BASED SCREENING
# ==================================================

def screen_campaign(row, metrics):
    """
    Identify signals worth investigating.
    A warning is not proof of a root cause or a reason to
    automatically pause a campaign.
    """

    goal = classify_objective(row)
    warnings = []
    data_gaps = []

    spend = metrics["spend"]
    installs = metrics["installs"]
    purchases = metrics["purchases"]
    revenue = metrics["revenue"]
    cpi = metrics["cpi"]
    cpa = metrics["purchase_cpa"]
    roas = metrics["roas"]

    if spend <= 0:
        warnings.append("Spend is zero or unavailable.")

    if goal == "INSTALLS":
        if installs <= 0:
            warnings.append("No installs recorded.")
            data_gaps.append(
                "Verify install tracking and attribution."
            )
        elif cpi is not None and cpi > TARGET_CPI * 1.2:
            warnings.append(
                f"CPI exceeds the illustrative review threshold "
                f"of {TARGET_CPI * 1.2:.2f}."
            )

    elif goal == "PURCHASES":
        if purchases <= 0:
            warnings.append("No purchases recorded.")
            data_gaps.append(
                "Verify purchase tracking and conversion volume."
            )

        if cpa is not None and cpa > TARGET_CPA * 1.2:
            warnings.append(
                f"Purchase CPA exceeds the illustrative review "
                f"threshold of {TARGET_CPA * 1.2:.2f}."
            )

        if roas is not None and roas < 1:
            warnings.append(
                "Reported revenue is below spend. Profitability "
                "cannot be determined without margin and cost data."
            )
        elif roas is not None and roas < TARGET_ROAS:
            warnings.append(
                f"ROAS is below the illustrative target "
                f"of {TARGET_ROAS:.2f}x."
            )

        if revenue <= 0 and purchases > 0:
            data_gaps.append(
                "Check purchase value and revenue tracking."
            )

    elif goal == "LEADS":
        warnings.append(
            "Verified lead count is unavailable in this dataset."
        )
        data_gaps.append(
            "Add a dedicated leads column to evaluate lead volume "
            "and cost per lead."
        )

    else:
        warnings.append(
            "Campaign objective could not be classified reliably."
        )
        data_gaps.append(
            "Confirm the campaign objective and campaign type."
        )

    if goal == "INSTALLS" and installs > 0 and purchases == 0:
        data_gaps.append(
            "Check downstream purchase tracking and user quality "
            "if purchases are an expected outcome."
        )

    return {
        "goal": goal,
        "warnings": warnings,
        "data_gaps": data_gaps,
    }


# ==================================================
# 7. PROMPT CONSTRUCTION
# ==================================================

def build_prompt(row, metrics, screening):
    """Build a campaign-specific evidence-based prompt."""

    campaign_name = row.get("campaign") or "Unnamed campaign"

    evidence = {
        "campaign_id": row.get("campaign_id", ""),
        "campaign": campaign_name,
        "platform": row.get("platform", "Unknown"),
        "campaign_type": row.get("campaign_type", "Unknown"),
        "market": row.get("market", "Unknown"),
        "objective": row.get("objective", "Unknown"),
        "classified_goal": screening["goal"],
        "metrics": metrics,
        "rule_based_warnings": screening["warnings"],
        "known_data_gaps": screening["data_gaps"],
        "illustrative_targets": {
            "target_cpi": TARGET_CPI,
            "target_purchase_cpa": TARGET_CPA,
            "target_roas": TARGET_ROAS,
        },
    }

    return f"""
You are AdPilot AI, a performance marketing investigator.

Analyze the supplied campaign evidence.

CAMPAIGN EVIDENCE:
{json.dumps(evidence, indent=2, ensure_ascii=False)}

RULES:
1. Use only supplied data as factual evidence.
2. Never invent metrics, events, causes, or business outcomes.
3. Separate observations from hypotheses.
4. High CPI or CPA does not prove its cause.
5. Do not instruct the system to execute budget changes.
6. Recommend practical experiments to test hypotheses.
7. Explain missing information in data_gaps.
8. ROAS alone does not establish profitability.
9. There is no verified leads column. Never describe purchases
   as verified leads.
10. Use low confidence when evidence is limited.
11. Thresholds are illustrative, not approved business targets.
12. Consider the campaign objective when interpreting metrics.
13. Do not present a hypothesis as a confirmed root cause.
14. Confidence describes the diagnosis, not whether a hypothesis
    is true.

Return JSON with exactly these fields:
- campaign: string
- problem: string
- evidence: list of strings
- hypotheses: list of strings
- experiments: list of strings
- data_gaps: list of strings
- confidence: low, medium, or high

Return JSON only. Do not add Markdown fences or extra text.
""".strip()


# ==================================================
# 8. REPORT VALIDATION
# ==================================================

def validate_report(report, expected_campaign=None):
    """Validate report fields, types, and confidence."""

    if not isinstance(report, dict):
        raise ValueError("Model response is not a JSON object.")

    missing = [
        field for field in REQUIRED_FIELDS
        if field not in report
    ]
    extra = [
        field for field in report
        if field not in REQUIRED_FIELDS
    ]

    if missing:
        raise ValueError(f"Missing report fields: {missing}")

    if extra:
        raise ValueError(f"Unexpected report fields: {extra}")

    if not isinstance(report["campaign"], str):
        raise ValueError("campaign must be a string.")

    if not isinstance(report["problem"], str):
        raise ValueError("problem must be a string.")

    for field in LIST_FIELDS:
        if not isinstance(report[field], list):
            raise ValueError(f"{field} must be a list.")

        if not all(isinstance(item, str) for item in report[field]):
            raise ValueError(f"Every item in {field} must be a string.")

    confidence = report["confidence"]

    if not isinstance(confidence, str):
        raise ValueError("confidence must be a string.")

    confidence = confidence.strip().lower()

    if confidence not in VALID_CONFIDENCE:
        raise ValueError(f"Invalid confidence: {confidence}")

    report["confidence"] = confidence

    if expected_campaign is not None:
        report["campaign"] = expected_campaign

    return report


# ==================================================
# 9. GEMINI INVESTIGATION
# ==================================================

def investigate_campaign(client, row, metrics, screening):
    """Call Gemini and validate one investigation report."""

    prompt = build_prompt(row, metrics, screening)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=REPORT_SCHEMA,
            temperature=0.2,
        ),
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    try:
        report = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise ValueError("Gemini returned invalid JSON.") from error

    campaign_name = str(
        row.get("campaign") or "Unnamed campaign"
    )

    report = validate_report(report, campaign_name)

    report["evidence"] = list(dict.fromkeys(
        screening["warnings"] + report["evidence"]
    ))

    report["data_gaps"] = list(dict.fromkeys(
        screening["data_gaps"] + report["data_gaps"]
    ))

    return report


# ==================================================
# 10. BACKWARD-COMPATIBLE FUNCTION
# ==================================================

def analyse_campaign(row, metrics, issue):
    """
    Keep the original function name for existing imports/tests.

    This function performs a live Gemini request when called.
    Importing the module does not call Gemini.
    """

    client = get_gemini_client()

    if isinstance(issue, dict):
        screening = {
            "goal": issue.get(
                "goal", classify_objective(row)
            ),
            "warnings": list(issue.get("warnings", [])),
            "data_gaps": list(issue.get("data_gaps", [])),
        }
    else:
        screening = screen_campaign(row, metrics)

        if issue:
            screening["warnings"] = list(dict.fromkeys(
                screening["warnings"] + [str(issue)]
            ))

    return investigate_campaign(client, row, metrics, screening)


# ==================================================
# 11. CSV INPUT AND OUTPUT
# ==================================================

def read_campaigns():
    """Read and validate the campaign CSV."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("campaigns.csv has no header row.")

        required_columns = {
            "campaign",
            "platform",
            "spend",
            "installs",
            "purchases",
            "revenue",
        }

        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                "campaigns.csv is missing columns: "
                + ", ".join(sorted(missing))
            )

        rows = list(reader)

    if not rows:
        raise ValueError("campaigns.csv contains no campaign rows.")

    return rows[:MAX_CAMPAIGNS]


def write_reports(reports):
    """Save successful and failed reports to CSV."""

    fieldnames = [
        "campaign_id",
        "campaign",
        "platform",
        "objective",
        "classified_goal",
        "spend",
        "installs",
        "purchases",
        "revenue",
        "cpi",
        "purchase_cpa",
        "roas",
        "ctr_percent",
        "cpc",
        "purchase_cvr_percent",
        "problem",
        "evidence",
        "hypotheses",
        "experiments",
        "data_gaps",
        "confidence",
        "status",
        "error",
    ]

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(reports)


# ==================================================
# 12. MAIN WORKFLOW
# ==================================================

def main():
    """Screen campaigns and run bounded Gemini investigations."""

    print("\n" + "=" * 65)
    print("ADPILOT AI — STRUCTURED CAMPAIGN INVESTIGATOR")
    print("=" * 65)

    try:
        rows = read_campaigns()
        client = get_gemini_client()
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"\nSetup error: {error}")
        return 1

    reports = []

    print(f"\nCampaigns selected: {len(rows)}")
    print(f"Maximum per run: {MAX_CAMPAIGNS}")

    for index, row in enumerate(rows, start=1):
        campaign_name = (
            row.get("campaign") or "Unnamed campaign"
        )

        print(
            f"\n[{index}/{len(rows)}] Investigating: "
            f"{campaign_name}"
        )

        metrics = calculate_metrics(row)
        screening = screen_campaign(row, metrics)

        base = {
            "campaign_id": row.get("campaign_id", ""),
            "campaign": campaign_name,
            "platform": row.get("platform", "Unknown"),
            "objective": row.get("objective", "Unknown"),
            "classified_goal": screening["goal"],
            "spend": metrics["spend"],
            "installs": metrics["installs"],
            "purchases": metrics["purchases"],
            "revenue": metrics["revenue"],
            "cpi": format_metric(metrics["cpi"]),
            "purchase_cpa": format_metric(metrics["purchase_cpa"]),
            "roas": format_metric(metrics["roas"], "x"),
            "ctr_percent": format_metric(
                metrics["ctr_percent"], "%"
            ),
            "cpc": format_metric(metrics["cpc"]),
            "purchase_cvr_percent": format_metric(
                metrics["purchase_cvr_percent"], "%"
            ),
        }

        try:
            report = investigate_campaign(
                client, row, metrics, screening
            )

            output_row = {
                **base,
                "problem": report["problem"],
                "evidence": json.dumps(
                    report["evidence"], ensure_ascii=False
                ),
                "hypotheses": json.dumps(
                    report["hypotheses"], ensure_ascii=False
                ),
                "experiments": json.dumps(
                    report["experiments"], ensure_ascii=False
                ),
                "data_gaps": json.dumps(
                    report["data_gaps"], ensure_ascii=False
                ),
                "confidence": report["confidence"],
                "status": "SUCCESS",
                "error": "",
            }

            print(f"  Confidence: {report['confidence']}")
            print(f"  Assessment: {report['problem']}")

        except Exception as error:
            output_row = {
                **base,
                "problem": "AI investigation could not be completed.",
                "evidence": json.dumps(
                    screening["warnings"], ensure_ascii=False
                ),
                "hypotheses": "[]",
                "experiments": "[]",
                "data_gaps": json.dumps(
                    screening["data_gaps"], ensure_ascii=False
                ),
                "confidence": "low",
                "status": "ERROR",
                "error": str(error),
            }

            print(f"  Investigation failed: {error}")

        reports.append(output_row)

    try:
        write_reports(reports)
    except OSError as error:
        print(f"\nCould not write output file: {error}")
        return 1

    success_count = sum(
        report["status"] == "SUCCESS" for report in reports
    )
    error_count = len(reports) - success_count

    print("\n" + "=" * 65)
    print("INVESTIGATION COMPLETED")
    print("=" * 65)
    print(f"Campaigns processed: {len(reports)}")
    print(f"Successful reports: {success_count}")
    print(f"Failed reports: {error_count}")
    print(f"Output file: {OUTPUT_FILE}")

    return 0 if error_count == 0 else 1


def analyse_campaign(row, metrics, issue):
    """Compatibility wrapper for existing tests and callers."""
    client = get_gemini_client()

    if isinstance(issue, dict):
        screening = {
            "goal": issue.get("goal", classify_objective(row)),
            "warnings": list(issue.get("warnings", [])),
            "data_gaps": list(issue.get("data_gaps", [])),
        }
    else:
        screening = screen_campaign(row, metrics)
        if issue:
            screening["warnings"] = list(
                dict.fromkeys(screening["warnings"] + [str(issue)])
            )

    return investigate_campaign(client, row, metrics, screening)

if __name__ == "__main__":
    sys.exit(main())
