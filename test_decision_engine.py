
import unittest
from decision_engine_v2 import evaluate_campaign


class TestAdPilot(unittest.TestCase):

    def test_scale_candidate(self):
        campaign = {
            "campaign": "Install Campaign",
            "platform": "Google",
            "objective": "App Install",
            "campaign_type": "UAC",
            "spend": "500",
            "installs": "100",
            "purchases": "0",
            "revenue": "0",
        }

        result = evaluate_campaign(campaign)
        self.assertEqual(result["decision"], "SCALE CANDIDATE")

    def test_high_cpa(self):
        campaign = {
            "campaign": "High CPA Campaign",
            "platform": "Meta",
            "objective": "Purchases",
            "campaign_type": "Shopping",
            "spend": "500",
            "installs": "0",
            "purchases": "2",
            "revenue": "1000",
        }

        result = evaluate_campaign(campaign)
        self.assertEqual(result["decision"], "NEEDS ATTENTION")

    def test_lead_generation(self):
        campaign = {
            "campaign": "Lead Campaign",
            "platform": "Google",
            "objective": "Lead Generation",
            "campaign_type": "Video",
            "spend": "500",
            "installs": "0",
            "purchases": "5",
            "revenue": "0",
        }

        result = evaluate_campaign(campaign)
        self.assertEqual(
            result["metric"],
            "Provisional cost per conversion",
        )
        self.assertIn("provisional", result["conversion_data_note"].lower())

    def test_unknown_objective(self):
        campaign = {
            "campaign": "Awareness Campaign",
            "platform": "Meta",
            "objective": "Brand Awareness",
            "campaign_type": "Video",
            "spend": "100",
            "installs": "0",
            "purchases": "0",
            "revenue": "0",
        }

        result = evaluate_campaign(campaign)
        self.assertEqual(result["decision"], "REVIEW OBJECTIVE")

    def test_zero_spend(self):
        campaign = {
            "campaign": "Zero Spend Campaign",
            "platform": "Google",
            "objective": "Purchases",
            "campaign_type": "Shopping",
            "spend": "0",
            "installs": "10",
            "purchases": "2",
            "revenue": "500",
        }

        result = evaluate_campaign(campaign)
        self.assertEqual(result["decision"], "CHECK DATA")


if __name__ == "__main__":
    unittest.main()
