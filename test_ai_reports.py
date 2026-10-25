
import csv
import json
import unittest

from structured_investigator import analyse_campaign


REPORT_FILE = "ai_recommendations.csv"

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


def validate_report(report):
    errors = []

    for field in REQUIRED_FIELDS:
        if not isinstance(report.get(field), str) or not report[field].strip():
            errors.append(f"Missing or empty field: {field}")

    for field in LIST_FIELDS:
        try:
            value = json.loads(report.get(field, ""))
            if not isinstance(value, list):
                errors.append(f"{field} must contain a JSON list")
        except (json.JSONDecodeError, TypeError):
            errors.append(f"{field} contains invalid JSON")

    if report.get("confidence") not in VALID_CONFIDENCE:
        errors.append("Invalid confidence level")

    return errors


class TestAIReports(unittest.TestCase):

    def test_report_file_exists_and_has_rows(self):
        with open(
            REPORT_FILE, newline="", encoding="utf-8"
        ) as file:
            reader = csv.DictReader(file)

            self.assertEqual(reader.fieldnames, REQUIRED_FIELDS)
            reports = list(reader)

        self.assertGreater(len(reports), 0)

    def test_all_saved_reports_are_valid(self):
        with open(
            REPORT_FILE, newline="", encoding="utf-8"
        ) as file:
            reports = list(csv.DictReader(file))

        for index, report in enumerate(reports, start=1):
            errors = validate_report(report)
            self.assertEqual(
                errors,
                [],
                f"Report {index}: {errors}",
            )

    def test_invalid_confidence_is_rejected(self):
        report = {
            "campaign": "Test Campaign",
            "problem": "Test problem",
            "evidence": "[]",
            "hypotheses": "[]",
            "experiments": "[]",
            "data_gaps": "[]",
            "confidence": "certain",
        }

        errors = validate_report(report)

        self.assertIn("Invalid confidence level", errors)

    def test_invalid_json_list_is_rejected(self):
        report = {
            "campaign": "Test Campaign",
            "problem": "Test problem",
            "evidence": "not valid JSON",
            "hypotheses": "[]",
            "experiments": "[]",
            "data_gaps": "[]",
            "confidence": "medium",
        }

        errors = validate_report(report)

        self.assertIn("evidence contains invalid JSON", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
