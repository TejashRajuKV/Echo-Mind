"""
claim_monitor.py — Opt-In Claim & Public Issue Monitoring Engine
===============================================================
Allows users to subscribe/follow a claim or public issue and receive alerts
only when significant new evidence, a correction, or an authoritative update appears.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

MONITOR_DB_PATH = Path(__file__).parent / "claim_monitors.db"


def _get_monitor_conn():
    conn = sqlite3.connect(MONITOR_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claim_monitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            email TEXT,
            claim_text TEXT NOT NULL,
            baseline_verdict TEXT NOT NULL,
            baseline_score INTEGER NOT NULL,
            baseline_evidence_count INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            last_checked TEXT NOT NULL,
            updates_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitor_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL,
            trigger_reason TEXT NOT NULL,
            new_verdict TEXT,
            new_score INTEGER,
            new_evidence_title TEXT,
            summary TEXT NOT NULL,
            notified_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (monitor_id) REFERENCES claim_monitors(id)
        )
    """)
    conn.commit()
    return conn


def subscribe_to_claim(
    session_id: str,
    claim_text: str,
    baseline_verdict: str,
    baseline_score: int,
    baseline_evidence_count: int = 0,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Subscribe a user to monitor a claim for future developments and corrections.
    """
    now = datetime.utcnow().isoformat() + "Z"
    conn = _get_monitor_conn()
    cursor = conn.cursor()

    # Check if already subscribed in this session
    existing = cursor.execute("""
        SELECT * FROM claim_monitors
        WHERE session_id = ? AND LOWER(claim_text) = LOWER(?) AND status = 'active'
    """, (session_id, claim_text.strip())).fetchone()

    if existing:
        conn.close()
        return {
            "status": "already_monitored",
            "monitor_id": existing["id"],
            "message": "You are already actively monitoring this claim.",
            "created_at": existing["created_at"],
        }

    cursor.execute("""
        INSERT INTO claim_monitors (
            session_id, email, claim_text, baseline_verdict, baseline_score,
            baseline_evidence_count, status, created_at, last_checked, updates_count
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, 0)
    """, (session_id, email or "", claim_text.strip(), baseline_verdict, baseline_score, baseline_evidence_count, now, now))

    monitor_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "subscribed",
        "monitor_id": monitor_id,
        "claim_text": claim_text,
        "baseline_verdict": baseline_verdict,
        "message": "Opt-in monitoring activated. You will be notified when significant new evidence or corrections emerge.",
        "created_at": now,
    }


def list_user_monitors(session_id: str) -> List[Dict[str, Any]]:
    """List all claims monitored by the active user session."""
    conn = _get_monitor_conn()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT m.*, 
               (SELECT COUNT(*) FROM monitor_notifications WHERE monitor_id = m.id AND is_read = 0) as unread_notifications
        FROM claim_monitors m
        WHERE m.session_id = ?
        ORDER BY m.id DESC
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_monitored_claim_for_updates(monitor_id: int) -> Dict[str, Any]:
    """
    Re-evaluates a monitored claim and checks if significant new evidence or
    a verdict correction has appeared since baseline.
    """
    conn = _get_monitor_conn()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM claim_monitors WHERE id = ?", (monitor_id,)).fetchone()
    if not row:
        conn.close()
        return {"status": "not_found"}

    from analysis_engine import analyze_claim
    res = analyze_claim(row["claim_text"], save_to_database=False)
    now = datetime.utcnow().isoformat() + "Z"

    current_verdict = res.get("classification", "Unknown")
    current_score = res.get("score", 50)
    current_evidence_sources = res.get("evidence_sources", [])
    current_evidence_count = len(current_evidence_sources)

    verdict_changed = current_verdict != row["baseline_verdict"]
    significant_new_evidence = current_evidence_count > row["baseline_evidence_count"] + 1
    score_swing = abs(current_score - row["baseline_score"]) >= 20

    has_update = verdict_changed or significant_new_evidence or score_swing

    if has_update:
        reason = "Verdict Shift" if verdict_changed else ("New Evidence Inflow" if significant_new_evidence else "Major Confidence Swing")
        top_src = current_evidence_sources[0].get("title", "") if current_evidence_sources else ""
        summary = f"Update detected ({reason}): Claim shifted from {row['baseline_verdict']} ({row['baseline_score']} pts) to {current_verdict} ({current_score} pts)."

        cursor.execute("""
            INSERT INTO monitor_notifications (
                monitor_id, trigger_reason, new_verdict, new_score, new_evidence_title,
                summary, notified_at, is_read
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (monitor_id, reason, current_verdict, current_score, top_src, summary, now))

        cursor.execute("""
            UPDATE claim_monitors
            SET last_checked = ?, updates_count = updates_count + 1
            WHERE id = ?
        """, (now, monitor_id))
    else:
        cursor.execute("UPDATE claim_monitors SET last_checked = ? WHERE id = ?", (now, monitor_id))

    conn.commit()
    conn.close()

    return {
        "monitor_id": monitor_id,
        "has_update": has_update,
        "current_verdict": current_verdict,
        "current_score": current_score,
        "last_checked": now,
    }


if __name__ == "__main__":
    sub = subscribe_to_claim("sess_test_99", "WHO approves new dengue vaccine", "Trustworthy", 88, 3)
    print("Subscribed test monitor:", sub["status"])
