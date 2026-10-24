"""Stance tagging and verdict reconciliation policy tests."""
import unittest

from evidence_engine import detect_evidence_stance
from verdict_policy import reconcile_verdict


class StanceTests(unittest.TestCase):
    def test_explicit_fact_check_false_rating_refutes(self):
        self.assertEqual(detect_evidence_stance("claim", "headline", "body", "False"), "refutes")

    def test_explicit_true_rating_supports(self):
        self.assertEqual(detect_evidence_stance("claim", "headline", "body", "True"), "supports")

    def test_generic_reporting_is_neutral(self):
        self.assertEqual(detect_evidence_stance("claim", "Officials discuss policy", "Meeting held Tuesday"), "neutral")

    def test_explicit_debunking_is_refuting(self):
        self.assertEqual(detect_evidence_stance("claim", "Fact check: false claim debunked", "Details"), "refutes")


class VerdictReconciliationTests(unittest.TestCase):
    def test_model_cannot_override_insufficient_evidence(self):
        verdict, _ = reconcile_verdict("Trustworthy", {"consensus_direction": "supported"}, [
            {"publisher": "one", "domain": "one.example"}
        ])
        self.assertEqual(verdict, "Suspicious")

    def test_conflict_forces_contested_result(self):
        verdict, _ = reconcile_verdict("Trustworthy", {
            "consensus_direction": "disputed", "conflict_detected": True
        }, [
            {"publisher": "one", "domain": "one.example"},
            {"publisher": "two", "domain": "two.example"},
        ])
        self.assertEqual(verdict, "Suspicious")

    def test_two_publisher_consensus_can_be_decisive(self):
        verdict, _ = reconcile_verdict("Suspicious", {"consensus_direction": "supported"}, [
            {"publisher": "one", "domain": "one.example"},
            {"publisher": "two", "domain": "two.example"},
        ])
        self.assertEqual(verdict, "Trustworthy")


if __name__ == "__main__":
    unittest.main()
