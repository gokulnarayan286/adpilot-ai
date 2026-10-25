
import json
import os
from pathlib import Path

from google import genai

from adpilot_csv import load_campaigns, analyze_campaign


CSV_FILE = Path(__file__).parent / "campaigns.csv"
TARGET_ROAS = 2.0

SYSTEM_INSTRUCTIONS = """
You are AdPilot AI, a careful performance marketing analyst.

Analyze only the campaign data and calculated metrics provided.

Your responsibilities:
1. Identify strong and weak campaign performance.
2. Compare platforms, markets, campaign types and objectives.
3. Explain potential performance issues.
4. Recommend experiments and budget changes for human review.
5. Highlight insufficient data and data-quality concerns.

Rules:
- Do not invent metrics or claim access to live ad accounts.
- Do not recommend scaling based on a single metric alone.
- Consider campaign objective and conversion volume.
- Treat ROAS below 1.0x as revenue below ad spend, not necessarily
  overall business loss because margins and other costs are unknown.
- Label recommendations as hypotheses to validate.
- Never execute budget changes.
- Keep the report practical and concise.
"""


def build_campaign_data():
    campaigns = load_campaigns(CSV_FILE)
    results = [analyze_campaign(c) for c in campaigns]

    total_spend = sum(c["spend"] for c in results)
    total_revenue = sum(c["revenue"] for c in results)
    total_installs = sum(c["installs"] for c in results)
    total_purchases = sum(c["purchases"] for c in results)
    total_clicks = sum(c["clicks"] for c in results)
    total_impressions = sum(c["impressions"] for c in results)

    overall = {
        "campaign_records": len(results),
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "total_installs": total_installs,
        "total_purchases": total_purchases,
        "overall_cpa": (
            round(total_spend / total_purchases, 2)
            if total_purchases else None
        ),
        "overall_roas": (
            round(total_revenue / total_spend, 2)
            if total_spend else None
        ),
        "overall_ctr_percent": (
            round(total_clicks / total_impressions * 100, 3)
            if total_impressions else None
        ),
    }

    # Summarize campaigns by platform.
    platform_summary = {}

    for c in results:
        platform = c["platform"]

        if platform not in platform_summary:
            platform_summary[platform] = {
                "spend": 0,
                "revenue": 0,
                "installs": 0,
                "purchases": 0,
                "campaign_count": 0,
            }

        group = platform_summary[platform]
        group["spend"] += c["spend"]
        group["revenue"] += c["revenue"]
        group["installs"] += c["installs"]
        group["purchases"] += c["purchases"]
        group["campaign_count"] += 1

    for group in platform_summary.values():
        group["roas"] = (
            round(group["revenue"] / group["spend"], 2)
            if group["spend"] else None
        )
        group["cpa"] = (
            round(group["spend"] / group["purchases"], 2)
            if group["purchases"] else None
        )
        group["spend"] = round(group["spend"], 2)
        group["revenue"] = round(group["revenue"], 2)

    # Provide individual campaign metrics to the AI.
    campaign_details = []

    for c in results:
        campaign_details.append({
            "campaign_id": c["campaign_id"],
            "campaign": c["campaign"],
            "platform": c["platform"],
            "campaign_type": c["campaign_type"],
            "market": c["market"],
            "objective": c["objective"],
            "spend": round(c["spend"], 2),
            "clicks": c["clicks"],
            "installs": c["installs"],
            "purchases": c["purchases"],
            "revenue": round(c["revenue"], 2),
            "cpi": round(c["cpi"], 2) if c["cpi"] is not None else None,
            "cpa": round(c["cpa"], 2) if c["cpa"] is not None else None,
            "roas": round(c["roas"], 2) if c["roas"] is not None else None,
        })

    return {
        "overall": overall,
        "platform_summary": platform_summary,
        "campaign_details": campaign_details,
        "target_roas_for_review": TARGET_ROAS,
    }


def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY is not configured in this terminal.")
        return

    client = genai.Client(api_key=api_key)
    data = build_campaign_data()

    prompt = f"""
{SYSTEM_INSTRUCTIONS}

Analyze the following campaign data.

Business context:
- Target ROAS for this exercise: {TARGET_ROAS}x.
- This is sample campaign data, not a live advertising account.
- Do not assume that every campaign shares the same objective.

DATA:
{json.dumps(data, indent=2)}

Produce a report with these sections:

1. EXECUTIVE SUMMARY
2. GOOGLE VS META
3. TOP 5 CAMPAIGNS TO INVESTIGATE FOR SCALING
4. TOP 5 CAMPAIGNS NEEDING ATTENTION
5. MARKET AND CAMPAIGN-TYPE INSIGHTS
6. THREE PRIORITY EXPERIMENTS
7. DATA LIMITATIONS AND NEXT STEPS

For each campaign recommendation, include its campaign ID and the
metric that supports the recommendation. Explain uncertainty where
necessary. Do not claim that recommendations have been executed.
"""

    print("\n===== ADPILOT AI: CSV-POWERED ANALYST =====")
    print(f"Campaign records loaded: {data['overall']['campaign_records']}")
    print("Sending summarized and campaign-level data to Gemini...")

    models_to_try = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
    ]

    for model in models_to_try:
        try:
            print(f"\nTrying model: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            print(f"\nReport generated using: {model}")
            print("\n===== ADPILOT AI REPORT =====\n")
            print(response.text)
            return

        except Exception as error:
            print(f"That model did not work: {error}")

    print("\nCould not generate the AI report.")
    print("Check your API key, model availability, and internet connection.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"\nAdPilot AI could not process the data: {error}")
