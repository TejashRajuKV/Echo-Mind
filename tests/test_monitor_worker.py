"""Tests for scheduled monitor notification delivery without real SMTP."""
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import claim_monitor
import monitor_worker


class MonitorWorkerTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = claim_monitor.MONITOR_DB_PATH
        self.tempdir = __import__("tempfile").TemporaryDirectory()
        claim_monitor.MONITOR_DB_PATH = Path(self.tempdir.name) / "monitors.db"
        conn = claim_monitor._get_monitor_conn()
        now = datetime.utcnow().isoformat() + "Z"
        cursor = conn.execute(
            """INSERT INTO claim_monitors
               (session_id, email, claim_text, baseline_verdict, baseline_score,
                baseline_evidence_count, status, created_at, last_checked, updates_count)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, 0)""",
            ("session-test", "tester@example.com", "Test claim", "Suspicious", 40, 1, now, now),
        )
        self.monitor_id = cursor.lastrowid
        conn.execute(
            """INSERT INTO monitor_notifications
               (monitor_id, trigger_reason, new_verdict, new_score, new_evidence_title,
                summary, notified_at, is_read, email_sent_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)""",
            (self.monitor_id, "Verdict Shift", "False", 20, "Source", "A test update was detected.", now),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tempdir.cleanup()
        claim_monitor.MONITOR_DB_PATH = self.original_db_path

    def test_successful_email_delivery_marks_notification_sent(self):
        sent = []
        with patch.object(monitor_worker, "send_notification", side_effect=lambda *args: sent.append(args) or True):
            monitor_worker.deliver_pending_notifications()
        self.assertEqual(len(sent), 1)
        conn = claim_monitor._get_monitor_conn()
        row = conn.execute("SELECT email_sent_at FROM monitor_notifications WHERE monitor_id=?", (self.monitor_id,)).fetchone()
        conn.close()
        self.assertIsNotNone(row["email_sent_at"])

    def test_failed_email_delivery_remains_pending_for_retry(self):
        with patch.object(monitor_worker, "send_notification", return_value=False):
            monitor_worker.deliver_pending_notifications()
        conn = claim_monitor._get_monitor_conn()
        row = conn.execute("SELECT email_sent_at FROM monitor_notifications WHERE monitor_id=?", (self.monitor_id,)).fetchone()
        conn.close()
        self.assertIsNone(row["email_sent_at"])


if __name__ == "__main__":
    unittest.main()
