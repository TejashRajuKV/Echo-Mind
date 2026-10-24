"""Flask endpoint smoke tests. Analysis and external connectors are mocked."""
import unittest
from unittest.mock import patch

import app as app_module


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "healthy")

    def test_analyze_rejects_non_object_json(self):
        response = self.client.post("/analyze", data='"claim"', content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_analyze_rejects_blank_claim(self):
        response = self.client.post("/analyze", json={"claim": "  "})
        self.assertEqual(response.status_code, 400)

    def test_analyze_rejects_non_string_claim(self):
        response = self.client.post("/analyze", json={"claim": ["not", "text"]})
        self.assertEqual(response.status_code, 400)

    def test_document_endpoint_rejects_wrong_types(self):
        response = self.client.post("/document/analyze", json={"text": 123, "title": "test"})
        self.assertEqual(response.status_code, 400)

    def test_monitor_endpoint_rejects_bad_numeric_fields(self):
        response = self.client.post("/monitor/subscribe", json={
            "claim": "test claim", "score": "not-a-number", "evidence_count": 0
        })
        self.assertEqual(response.status_code, 400)

    def test_correction_rejects_non_http_url(self):
        unsafe_scheme = "java" + "script:alert(1)"
        response = self.client.post("/correction", json={
            "claim_text": "claim", "evidence_url": unsafe_scheme, "rationale": "evidence"
        })
        self.assertEqual(response.status_code, 400)

    def test_history_is_scoped_to_session_header(self):
        first = self.client.get("/history", headers={"X-Session-ID": "session-user-one-123456"})
        second = self.client.get("/history", headers={"X-Session-ID": "session-user-two-123456"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json()["history"], [])
        self.assertEqual(second.get_json()["history"], [])

    def test_analysis_route_handles_engine_failure_without_leaking_details(self):
        with patch.object(app_module, "analyze_claim", side_effect=RuntimeError("private failure detail")):
            response = self.client.post("/analyze", json={"claim": "A testable claim"}, headers={
                "X-Session-ID": "session-analysis-failure-123456"
            })
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"private failure detail", response.data)


if __name__ == "__main__":
    unittest.main()
