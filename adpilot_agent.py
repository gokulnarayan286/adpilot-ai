
import os
import json
import time
from google import genai
from google.genai import types


# ==========================================
# ADPILOT AI - LESSON 4
# Python Decision Engine + Gemini
# ==========================================

campaigns = [
    {"name": "Google Search", "spend": 5000, "installs": 1000, "purchases": 80},
    {"name": "Meta Prospecting", "spend": 8000, "installs": 1200, "purchases": 50},
    {"name": "Google UAC", "spend": 6000, "installs": 1500, "purchases": 100},
]

TARGET_CPA = 80
MIN_PURCHASES = 30

# Models are tried in order. Availability depends on your API access.
MODEL_CANDIDATES = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]


def analyze_campaign(campaign):
    """Calculate metrics and apply deterministic decision rules."""
    spend = campaign["spend"]
    installs = campaign["installs"]
    purchases = campaign["purchases"]

    cpi = round(spend / installs, 2) if installs > 0 else None
    cpa = round(spend / purchases, 2) if purchases > 0 else None
    purchase_rate = (
        round(purchases / installs * 100, 2)
        if installs > 0 else None
    )

    if purchases < MIN_PURCHASES or cpa is None:
        decision = "INVESTIGATE"
        reason = "Insufficient purchase data"
    elif cpa <= TARGET_CPA * 0.80:
        decision = "SCALE_CANDIDATE"
        reason = "CPA is at least 20% below target"
    elif cpa > TARGET_CPA * 1.50:
        decision = "REDUCE_CANDIDATE"
        reason = "CPA is more than 50% above target"
    else:
        decision = "INVESTIGATE"
        reason = "Performance needs further analysis"

    return {
        "name": campaign["name"],
        "spend_inr": spend,
        "installs": installs,
        "purchases": purchases,
        "CPI_inr": cpi,
        "CPA_inr": cpa,
        "purchase_rate_percent": purchase_rate,
        "target_CPA_inr": TARGET_CPA,
        "decision": decision,
        "decision_reason": reason,
    }


def generate_ai_report(report_data):
    """Ask Gemini to explain Python's calculations and decisions."""
    client = genai.Client(
        http_options=types.HttpOptions(timeout=120000)
    )

    prompt = f"""
You are AdPilot AI, a performance marketing analyst.

Python has already calculated these metrics and applied decision rules:
{json.dumps(report_data, indent=2)}

Your task:
1. Summarize overall performance.
2. Explain each campaign's assigned decision.
3. Recommend three practical next steps.
4. Identify what additional data should be checked before budget changes.

Important safeguards:
- Treat Python's calculations and decisions as the source of truth.
- Do not invent metrics.
- A candidate decision is not an instruction to change a live budget.
- Consider attribution, conversion lag, retention, lifetime value, and data quality.
- Clearly distinguish facts from hypotheses.
- Do not claim to access live ad accounts.
- Use Indian rupees.
"""

    last_error = None

    for model_name in MODEL_CANDIDATES:
        print(f"\nTrying Gemini model: {model_name}")

        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if response and response.text:
                    return model_name, response.text

                print("Empty response; trying another model.")
                break

            except Exception as error:
                last_error = error
                print(
                    f"Attempt {attempt + 1} failed: "
                    f"{type(error).__name__}"
                )

                if attempt == 0:
                    time.sleep(2)

        print("Moving to the next model...")

    return None, None if last_error is None else (None, str(last_error))


def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is missing. Configure it in this terminal.")
        return

    print("\n===== ADPILOT AI: PYTHON ANALYSIS =====")

    report_data = [
        analyze_campaign(campaign)
        for campaign in campaigns
    ]

    for item in report_data:
        print(
            f'{item["name"]}: CPA ₹{item["CPA_inr"]:.2f} | '
            f'Decision: {item["decision"]}'
        )

    print("\n===== ADPILOT AI: GEMINI ANALYSIS =====")

    result = generate_ai_report(report_data)

    if isinstance(result, tuple) and len(result) == 2:
        model_name, report = result
    else:
        model_name, report = None, None

    if model_name and report:
        print(f"\nReport generated with: {model_name}")
        print("\n" + report)
    else:
        print("\nGemini could not generate the report.")
        print("Your Python decisions are still available:")
        print(json.dumps(report_data, indent=2))
        if report:
            print("Last error:", report)


if __name__ == "__main__":
    main()
