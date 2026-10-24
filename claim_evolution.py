"""
claim_evolution.py — Claim Evolution and Mutation Tracker
=========================================================
Tracks how claims change over time in wording, evidence accumulation,
and verdict drift (e.g. from early viral rumor to refuted misinformation).
"""

import sqlite3
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

EVOLUTION_DB_PATH = Path(__file__).parent / "claim_evolution.db"


def _get_evolution_conn():
    conn = sqlite3.connect(EVOLUTION_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claim_clusters (
            cluster_id TEXT PRIMARY KEY,
            canonical_claim TEXT NOT NULL,
            category TEXT,
            first_seen TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            total_variants INTEGER DEFAULT 1,
            current_verdict TEXT NOT NULL,
            current_score INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claim_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id TEXT NOT NULL,
            variant_text TEXT NOT NULL,
            verdict TEXT NOT NULL,
            score INTEGER NOT NULL,
            evidence_count INTEGER DEFAULT 0,
            primary_source TEXT,
            notes TEXT,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY (cluster_id) REFERENCES claim_clusters(cluster_id)
        )
    """)
    conn.commit()
    return conn


def _generate_claim_fingerprint(text: str) -> str:
    """
    Generate a normalized semantic fingerprint based on significant content words.
    Ignores punctuation, casing, and stop words so paraphrased variants cluster together.
    """
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'a', 'an', 'that', 'this', 'it', 'they', 'them',
        'has', 'have', 'had', 'will', 'would', 'could', 'should', 'can', 'about', 'says'
    }
    words = re.findall(r'\b[a-zA-Z0-9_\u0900-\u0D7F]{3,}\b', text.lower())
    significant = sorted(list(set(w for w in words if w not in stop_words)))
    sig_str = " ".join(significant[:8]) if significant else text.strip().lower()
    return hashlib.sha256(sig_str.encode('utf-8')).hexdigest()[:16]


def record_claim_evolution(
    claim_text: str,
    verdict: str,
    score: int,
    evidence_count: int = 0,
    primary_source: str = "",
    category: str = "General",
    notes: str = ""
) -> Dict[str, Any]:
    """
    Record an analyzed claim into the evolution graph.
    If a similar claim already exists, links it into the timeline to reveal verdict drift.
    """
    cluster_id = _generate_claim_fingerprint(claim_text)
    now = datetime.utcnow().isoformat() + "Z"
    conn = _get_evolution_conn()
    cursor = conn.cursor()

    row = cursor.execute("SELECT * FROM claim_clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
    if row is None:
        cursor.execute("""
            INSERT INTO claim_clusters (
                cluster_id, canonical_claim, category, first_seen, last_updated,
                total_variants, current_verdict, current_score
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (cluster_id, claim_text, category, now, now, verdict, score))
        is_new_cluster = True
    else:
        cursor.execute("""
            UPDATE claim_clusters
            SET last_updated = ?,
                total_variants = total_variants + 1,
                current_verdict = ?,
                current_score = ?
            WHERE cluster_id = ?
        """, (now, verdict, score, cluster_id))
        is_new_cluster = False

    cursor.execute("""
        INSERT INTO claim_timeline (
            cluster_id, variant_text, verdict, score, evidence_count,
            primary_source, notes, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cluster_id, claim_text, verdict, score, evidence_count, primary_source, notes, now))

    conn.commit()
    conn.close()

    return {
        "cluster_id": cluster_id,
        "is_new_cluster": is_new_cluster,
        "recorded_at": now,
    }


def get_claim_evolution_timeline(claim_text: str) -> Dict[str, Any]:
    """
    Retrieve the chronological evolution history of a claim and its mutations.
    """
    cluster_id = _generate_claim_fingerprint(claim_text)
    conn = _get_evolution_conn()
    cursor = conn.cursor()

    cluster = cursor.execute("SELECT * FROM claim_clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
    if cluster is None:
        conn.close()
        return {
            "cluster_id": cluster_id,
            "has_evolution_history": False,
            "canonical_claim": claim_text,
            "timeline": [],
            "verdict_drift_detected": False,
        }

    rows = cursor.execute("""
        SELECT variant_text, verdict, score, evidence_count, primary_source, notes, recorded_at
        FROM claim_timeline
        WHERE cluster_id = ?
        ORDER BY id ASC
    """, (cluster_id,)).fetchall()
    conn.close()

    timeline = [dict(r) for r in rows]
    # Check if verdict shifted over time (e.g. from Suspicious to False or Trustworthy)
    verdicts = [item["verdict"] for item in timeline]
    drift_detected = len(set(verdicts)) > 1

    return {
        "cluster_id": cluster_id,
        "has_evolution_history": len(timeline) > 1,
        "canonical_claim": cluster["canonical_claim"],
        "category": cluster["category"],
        "first_seen": cluster["first_seen"],
        "last_updated": cluster["last_updated"],
        "total_variants": cluster["total_variants"],
        "verdict_drift_detected": drift_detected,
        "verdicts_history": list(set(verdicts)),
        "timeline": timeline,
    }


if __name__ == "__main__":
    test_claim = "Drinking hot lemon water kills coronavirus instantly"
    res1 = record_claim_evolution(test_claim, "Suspicious", 45, evidence_count=1, notes="Initial viral post")
    res2 = record_claim_evolution("Lemon water cure kills COVID 19", "False", 15, evidence_count=4, primary_source="WHO", notes="Debunked by WHO")
    history = get_claim_evolution_timeline(test_claim)
    print("Evolution timeline variants:", len(history["timeline"]))
    print("Verdict drift detected:", history["verdict_drift_detected"])
