
import csv
import json
import os

from google import genai
from campaign_investigator import investigate_campaign


CSV_FILE = "campaigns.csv"
MODEL_NAME = "gemini-3.5-flash-lite"


def load_campaigns():
    with open(
        CSV_FILE,
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


def select_campaigns(campaigns, limit=10):
    results = []

    for row in campaigns:
        result = investigate_campaign(row)

        # Prioritize campaigns with investigation warnings.
        if any(
            "above" in finding.lower()
            or "check" in finding.lower()
            or "cannot evaluate" in finding.lower()
            or "zero" in finding.lower()
            for finding in result["findings"]
        ):
            results.append(result)

        if len(results) >= limit:
            break

    return results


def create_prompt(results):
    return f"""
You are AdPilot AI, a performance marketing analyst.

Analyse the campaign investigation results below.

Rules:
1. Use the supplied metrics as evidence.
2. Separate facts from hypotheses.
3. Suggest practical experiments, not unsupported conclusions.
4. Do not recommend automatic budget changes.
5. Lead-generation campaigns have no verified leads column.
6. Never treat purchases as verified leads.
7. The targets are illustrative practice thresholds, not validated
   business targets.
8. If data is insufficient, explain what additional data is needed.

For each campaign, provide:
- Campaign and platform
- Main performance concern
- Evidence from the metrics
- Two or three possible explanations, labelled as hypotheses
- Two practical experiments
- Additional data needed
- Confidence level: low, medium, or high

Finish with a short executive summary.

Campaign investigation data:
{json.dumps(results, indent=2)}
"""


def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set.")
        return

    campaigns = load_campaigns()

    if not campaigns:
        print("No campaigns found in the CSV.")
        return

    results = select_campaigns(campaigns, limit=10)

    if not results:
        print("No campaigns selected for investigation.")
        return

    print("Total campaigns:", len(campaigns))
    print("Campaigns selected for AI analysis:", len(results))
    print("\nSending campaign evidence to Gemini...")

    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"]
    )

    prompt = create_prompt(results)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    print("\n" + "=" * 60)
    print("ADPILOT AI — CAMPAIGN INVESTIGATION REPORT")
    print("=" * 60)
    print(response.text)


if __name__ == "__main__":
    main()
