"""Deterministic regression tests; no live APIs, credentials, or network calls required."""
import json
import unittest
from pathlib import Path

from verification_engine import evaluate_conflict_and_consensus, compute_credibility_score
from shareable_report import generate_shareable_report_html, generate_claim_review_jsonld


def source(domain, stance, authority=90, url=None, title="Evidence"):
    return {
        "domain": domain, "publisher": domain, "stance": stance,
        "authority_score": authority, "url": url or f"https://{domain}/story",
        "title": title, "cluster_id": domain,
    }


class VerificationPolicyTests(unittest.TestCase):
    def test_empty_evidence_is_unknown_not_consensus(self):
        result = evaluate_conflict_and_consensus([])
        self.assertEqual(result["consensus_direction"], "unknown")
        self.assertEqual(result["consensus_percentage"], 0.0)
        self.assertIn("Insufficient", result["status"])

    def test_single_publisher_never_counts_as_consensus(self):
        result = evaluate_conflict_and_consensus([source("one.example", "supports")])
        self.assertEqual(result["consensus_direction"], "unknown")
        self.assertEqual(result["independent_publisher_count"], 1)

    def test_mirrored_sources_from_same_domain_are_not_independent(self):
        result = evaluate_conflict_and_consensus([
            source("same.example", "supports", url="https://same.example/a"),
            source("same.example", "supports", url="https://same.example/b"),
        ])
        self.assertEqual(result["independent_publisher_count"], 1)
        self.assertEqual(result["consensus_direction"], "unknown")

    def test_conflicting_independent_publishers_are_disputed(self):
        result = evaluate_conflict_and_consensus([
            source("support.example", "supports"),
            source("refute.example", "refutes"),
        ])
        self.assertTrue(result["conflict_detected"])
        self.assertEqual(result["consensus_direction"], "disputed")

    def test_same_publisher_with_conflicting_stances_does_not_count_twice(self):
        result = evaluate_conflict_and_consensus([
            source("one.example", "supports"),
            source("one.example", "refutes"),
        ])
        self.assertEqual(result["independent_publisher_count"], 1)
        self.assertEqual(result["consensus_direction"], "unknown")

    def test_unsupported_or_neutral_sources_do_not_create_truth_verdict(self):
        result = evaluate_conflict_and_consensus([
            source("a.example", "neutral"), source("b.example", "neutral")
        ])
        self.assertEqual(result["consensus_direction"], "unknown")
        self.assertNotIn("Strong Consensus", result["status"])

    def test_unverified_score_is_abstention(self):
        result = compute_credibility_score([], evaluate_conflict_and_consensus([]))
        self.assertEqual(result["verdict"], "Unverified")


class ReportSecurityTests(unittest.TestCase):
    def test_claim_and_source_fields_are_html_escaped(self):
        payload = {
            "claim": '<img src=x onerror=alert(1)>',
            "classification": "Suspicious",
            "explanation": '<script>alert("x")</script>',
            "evidence_sources": [{
                "publisher": '<svg onload=alert(1)>',
                "stance": "neutral", "authority_score": 50,
                "url": "javascript:alert(1)", "date": "today",
            }],
        }
        report = generate_shareable_report_html(payload, payload["claim"])
        self.assertNotIn('<img src=x', report)
        self.assertNotIn('<script>alert("x")</script>', report)
        self.assertNotIn('href="javascript:', report)
        self.assertIn("&lt;img", report)
        self.assertIn("&lt;svg", report)

    def test_jsonld_cannot_break_out_of_script_context(self):
        closing = "<" + "/script>"
        evil = closing + "<script>alert(1)" + closing
        report = generate_shareable_report_html({"classification": "Suspicious"}, evil)
        self.assertNotIn(closing + "<script>alert(1)", report.lower())
        self.assertIn(r"\u003c/script\u003e", report.lower())

    def test_unsafe_source_schemes_are_not_linked(self):
        report = generate_shareable_report_html({
            "classification": "Suspicious",
            "evidence_sources": [{"publisher": "Test", "url": "data:text/html,hello"}],
        }, "Test")
        self.assertNotIn('href="data:', report)


class DatasetIntegrityTests(unittest.TestCase):
    def test_labelled_dataset_has_required_fields(self):
        path = Path(__file__).parent / "fixtures" / "labelled_claims.json"
        dataset = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(dataset["examples"]), 5)
        for item in dataset["examples"]:
            self.assertTrue(item["claim"])
            self.assertIn(item["expected_verdict"], {"Trustworthy", "False", "Suspicious"})
            self.assertIn("expected_evidence_state", item)


if __name__ == "__main__":
    unittest.main()
