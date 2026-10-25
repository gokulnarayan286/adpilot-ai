
import os
import json
import time
from google import genai
from google.genai import types


# ==========================================
# ADPILOT AI - CAMPAIGN PERFORMANCE ANALYST
# ==========================================

# 1. Mock campaign data
campaigns = [
    {
        "name": "Google Search",
        "spend": 5000,
        "installs": 1000,
        "purchases": 80
    },
    {
        "name": "Meta Prospecting",
        "spend": 8000,
        "installs": 1200,
        "purchases": 50
    },
    {
        "name": "Google UAC",
        "spend": 6000,
        "installs": 1500,
        "purchases": 100
    }
]

TARGET_CPA = 80


# 2. Check API key
if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit(
        "\nGEMINI_API_KEY is missing.\n"
        "Set your API key in the terminal before running this program."
    )


# 3. Calculate campaign metrics using Python
campaign_report = []

for campaign in campaigns:
    spend = campaign["spend"]
    installs = campaign["installs"]
    purchases = campaign["purchases"]

    cpi = round(spend / installs, 2) if installs > 0 else None
    cpa = round(spend / purchases, 2) if purchases > 0 else None

    purchase_rate = (
        round(purchases / installs * 100, 2)
        if installs > 0 else None
    )

    if cpa is None:
        status = "Insufficient purchase data"
    elif cpa > TARGET_CPA:
        status = "Above target"
    else:
        status = "Within target"

    campaign_report.append({
        "campaign": campaign["name"],
        "spend_inr": spend,
        "installs": installs,
        "purchases": purchases,
        "CPI_inr": cpi,
        "CPA_inr": cpa,
        "purchase_rate_percent": purchase_rate,
        "target_CPA_inr": TARGET_CPA,
        "status": status
    })


# 4. Prepare the AI prompt
prompt = f"""
You are AdPilot AI, a performance marketing analyst.

Analyze the following Python-calculated campaign data:

{json.dumps(campaign_report, indent=2)}

The target CPA is ₹{TARGET_CPA}.

Create a practical report containing:

1. Executive summary.
2. Campaign-by-campaign performance.
3. Best and worst campaigns based on CPA.
4. Three actionable optimization recommendations.
5. Additional data to check before changing budgets.

Rules:
- Use the supplied metrics as the source of truth.
- Do not invent data or claim unsupported causes.
- Distinguish observations from hypotheses.
- Do not claim access to live advertising accounts.
- Do not change budgets or execute advertising actions.
- Use Indian rupees.
- Keep the report clear and concise.
"""


# 5. Configure Gemini
client = genai.Client(
    http_options=types.HttpOptions(timeout=120000)
)


# 6. Try multiple models with automatic fallback
MODEL_CANDIDATES = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

response = None
successful_model = None
last_error = None

print("\n==========================================")
print(" ADPILOT AI: GENERATING CAMPAIGN REPORT")
print("==========================================")

for model_name in MODEL_CANDIDATES:
    print(f"\nTrying model: {model_name}")

    # Retry transient server failures twice before switching models.
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text:
                successful_model = model_name
                break

            print("Model returned an empty response.")
            break

        except Exception as error:
            last_error = error
            error_type = type(error).__name__
            error_message = str(error)

            print(
                f"Attempt {attempt + 1} failed: "
                f"{error_type}"
            )

            # Do not retry authentication, permission,
            # or invalid-request errors across the same model.
            message_lower = error_message.lower()

            permanent_error = any(term in message_lower for term in [
                "api key not valid",
                "invalid api key",
                "permission_denied",
                "unauthenticated",
                "api_key_invalid",
                "not found",
                "unsupported"
            ])

            if permanent_error:
                print("This may be an API access or model-name issue.")
                break

            if attempt == 0:
                wait_seconds = 3
                print(f"Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)

    if successful_model:
        break

    response = None
    print("Moving to the next model...")


# 7. Display the final report
if response and response.text:
    print("\n==========================================")
    print(" CAMPAIGN PERFORMANCE REPORT")
    print("==========================================")
    print(f"Model used: {successful_model}\n")
    print(response.text)

else:
    print("\n==========================================")
    print(" AI REPORT COULD NOT BE GENERATED")
    print("==========================================")

    print("\nPython-calculated campaign metrics are still available:")
    print(json.dumps(campaign_report, indent=2))

    if last_error:
        print("\nLast error type:", type(last_error).__name__)
        print("Last error:", str(last_error))

    print(
        "\nCheck your API key, available model names, "
        "API quota, and temporary service availability."
    )

print("\n==========================================")
print(" ADPILOT AI PROCESS FINISHED")
print("==========================================")
