"""Privacy-aware investigation memory and incremental verification for Echo Mind.

Conversation/investigation memory is session-scoped. Only normalized, source-backed
analysis snapshots are shared through the evidence cache. Cached verdicts expire
quickly for time-sensitive claims and are always labelled with their age.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

DB_PATH = Path(__file__).parent / "context_memory.db"
DEFAULT_TTL_SECONDS = 6 * 60 * 60
LIVE_TTL_SECONDS = 15 * 60
MAX_CLAIM_CHARS = 2000
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "was", "were", "are",
    "is", "to", "of", "in", "on", "a", "an", "by", "as", "it", "its", "will",
    "be", "has", "have", "had", "about", "says", "said", "claim", "viral",
    "क्या", "है", "का", "की", "के", "और", "में", "को", "से", "यह", "कि",
}

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).isoformat()

def normalize_claim(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("claim must be a string")
    text = text.strip().lower()
    if not text or len(text) > MAX_CLAIM_CHARS:
        raise ValueError("claim must be between 1 and 2000 characters")
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"[^\w\u0900-\u0d7f]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()

def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_claim(text).encode("utf-8")).hexdigest()

def _tokens(text: str) -> set[str]:
    return {w for w in normalize_claim(text).split() if len(w) > 1 and w not in STOP_WORDS}

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS investigations (
      id TEXT PRIMARY KEY, session_id TEXT NOT NULL, claim TEXT NOT NULL,
      fingerprint TEXT NOT NULL, language TEXT, verdict TEXT, score REAL,
      status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL, last_verified_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_investigations_session_updated
      ON investigations(session_id, updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_investigations_fingerprint
      ON investigations(fingerprint);
    CREATE TABLE IF NOT EXISTS claim_relationships (
      left_id TEXT NOT NULL, right_id TEXT NOT NULL, relation TEXT NOT NULL,
      similarity REAL NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(left_id, right_id), FOREIGN KEY(left_id) REFERENCES investigations(id) ON DELETE CASCADE,
      FOREIGN KEY(right_id) REFERENCES investigations(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS evidence_cache (
      fingerprint TEXT PRIMARY KEY, claim TEXT NOT NULL, result_json TEXT NOT NULL,
      sources_json TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
      last_hit_at TEXT, hit_count INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS investigation_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, investigation_id TEXT NOT NULL,
      event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS memory_preferences (
      session_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1,
      retention_days INTEGER NOT NULL DEFAULT 90, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS claim_aliases (
      id INTEGER PRIMARY KEY AUTOINCREMENT, investigation_id TEXT NOT NULL,
      session_id TEXT NOT NULL, alias_text TEXT NOT NULL, alias_fingerprint TEXT NOT NULL,
      language TEXT, created_at TEXT NOT NULL,
      UNIQUE(investigation_id, alias_fingerprint),
      FOREIGN KEY(investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
    );
    """)
    return conn

def _safe_sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result.get("sources") or result.get("evidence") or []
    if isinstance(raw, dict):
        raw = raw.get("sources", [])
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:100]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link")
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        out.append({
            "title": str(item.get("title") or item.get("name") or "")[:500],
            "url": url[:2048],
            "publisher": str(item.get("publisher") or item.get("source") or parsed.netloc)[:200],
            "published_at": item.get("published_at") or item.get("date"),
        })
    return out

def _ttl_for_claim(claim: str) -> int:
    live_terms = re.compile(r"\b(today|now|currently|latest|current|this week|202[5-9]|202[0-9]|price|rate|captain|minister|result|election|weather|score|breaking)\b", re.I)
    return LIVE_TTL_SECONDS if live_terms.search(claim) else DEFAULT_TTL_SECONDS

def get_preferences(session_id: str) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute("SELECT * FROM memory_preferences WHERE session_id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else {"session_id": session_id, "enabled": 1, "retention_days": 90}

def set_preferences(session_id: str, enabled: bool, retention_days: int = 90) -> dict[str, Any]:
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    if not isinstance(retention_days, int) or not 1 <= retention_days <= 365:
        raise ValueError("retention_days must be between 1 and 365")
    conn = _conn()
    conn.execute("""INSERT INTO memory_preferences(session_id,enabled,retention_days,updated_at)
      VALUES(?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET enabled=excluded.enabled,
      retention_days=excluded.retention_days,updated_at=excluded.updated_at""",
      (session_id, int(enabled), retention_days, _iso()))
    conn.commit()
    conn.close()
    if not enabled:
        clear_private_memory(session_id, preserve_preferences=True)
    return {"enabled": enabled, "retention_days": retention_days}

def clear_private_memory(session_id: str, preserve_preferences: bool = True) -> int:
    conn = _conn()
    ids = [r["id"] for r in conn.execute("SELECT id FROM investigations WHERE session_id=?", (session_id,))]
    for inv_id in ids:
        conn.execute("DELETE FROM investigations WHERE id=?", (inv_id,))
    if not preserve_preferences:
        conn.execute("DELETE FROM memory_preferences WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()
    return len(ids)

def delete_investigation(session_id: str, investigation_id: str) -> bool:
    conn = _conn()
    cursor = conn.execute("DELETE FROM investigations WHERE id=? AND session_id=?", (investigation_id, session_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def _event(conn: sqlite3.Connection, inv_id: str, kind: str, payload: dict[str, Any]) -> None:
    conn.execute("INSERT INTO investigation_events(investigation_id,event_type,payload_json,created_at) VALUES(?,?,?,?)",
                 (inv_id, kind, json.dumps(payload, ensure_ascii=False)[:20000], _iso()))

def related_investigations(session_id: str, claim: str, limit: int = 8) -> list[dict[str, Any]]:
    query_tokens = _tokens(claim)
    if not query_tokens:
        return []
    conn = _conn()
    prefs = conn.execute("SELECT enabled,retention_days FROM memory_preferences WHERE session_id=?", (session_id,)).fetchone()
    if prefs and not prefs["enabled"]:
        conn.close()
        return []
    retention = int(prefs["retention_days"]) if prefs else 90
    cutoff = _iso(utc_now() - timedelta(days=retention))
    rows = conn.execute("""SELECT id,claim,fingerprint,verdict,score,status,created_at,updated_at,last_verified_at
      FROM investigations WHERE session_id=? AND updated_at>=? ORDER BY updated_at DESC LIMIT 250""",
      (session_id, cutoff)).fetchall()
    conn.close()
    matches = []
    for row in rows:
        words = _tokens(row["claim"])
        if not words:
            continue
        union = query_tokens | words
        score = len(query_tokens & words) / len(union) if union else 0
        exact = fingerprint(claim) == row["fingerprint"]
        # Strong token overlap only; a shared generic term is not a relation.
        if exact or (score >= 0.28 and len(query_tokens & words) >= 2):
            matches.append({**dict(row), "similarity": round(1.0 if exact else score, 3),
                            "relation": "exact" if exact else "related"})
    matches.sort(key=lambda x: (x["relation"] == "exact", x["similarity"], x["updated_at"]), reverse=True)
    return matches[:max(1, min(int(limit), 20))]

def prepare_context(session_id: str, claim: str) -> dict[str, Any]:
    prefs = get_preferences(session_id)
    matches = related_investigations(session_id, claim) if prefs.get("enabled", 1) else []
    aliases = find_alias_matches(session_id, claim) if prefs.get("enabled", 1) else []
    known_ids = {item.get("id") for item in matches}
    for item in aliases:
        item["id"] = item.get("investigation_id")
        if item["id"] not in known_ids:
            matches.append(item)
            known_ids.add(item["id"])
    cache = get_cached_analysis(claim)
    return {
        "memory_enabled": bool(prefs.get("enabled", 1)),
        "matches": matches,
        "cache": cache,
        "mode": "exact_cache" if cache and cache.get("fresh") else ("incremental" if matches else "fresh"),
        "guidance": (
            "Revalidate material changes, dates, amounts, locations, and time-sensitive claims. "
            "Prior verdicts and user-provided statements are context, not evidence. Do not infer a verdict from similarity."
        ),
    }

def record_investigation(session_id: str, claim: str, result: dict[str, Any],
                         related: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    now = _iso()
    inv_id = hashlib.sha256((session_id + "|" + fingerprint(claim) + "|" + now).encode()).hexdigest()[:24]
    verdict = str(result.get("classification", "Unknown"))[:100]
    score = result.get("score")
    try:
        score = float(score) if score is not None else None
    except (ValueError, TypeError):
        score = None
    conn = _conn()
    conn.execute("""INSERT INTO investigations(id,session_id,claim,fingerprint,language,verdict,score,status,created_at,updated_at,last_verified_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (inv_id, session_id, claim[:MAX_CLAIM_CHARS], fingerprint(claim), result.get("language"),
       verdict, score, "complete", now, now, now))
    _event(conn, inv_id, "analysis_completed", {"verdict": verdict, "score": score,
      "source_count": len(_safe_sources(result))})
    for old in (related or [])[:8]:
        left, right = sorted((inv_id, old["id"]))
        conn.execute("""INSERT OR IGNORE INTO claim_relationships(left_id,right_id,relation,similarity,created_at)
          VALUES(?,?,?,?,?)""", (left, right, old["relation"], old["similarity"], now))
    conn.commit()
    conn.close()
    cache_analysis(claim, result)
    return {"id": inv_id, "created_at": now, "related_count": len(related or [])}

def cache_analysis(claim: str, result: dict[str, Any]) -> None:
    # Store only source-backed analysis output; no session identifiers or user preferences.
    key = fingerprint(claim)
    now = utc_now()
    ttl = _ttl_for_claim(claim)
    safe_result = dict(result)
    safe_result.pop("session", None)
    safe_result.pop("gamification", None)
    safe_result.pop("personalization", None)
    sources = _safe_sources(result)
    # Do not share guesses, empty-evidence outputs, or manually created workspace placeholders.
    if not sources:
        return
    conn = _conn()
    conn.execute("""INSERT INTO evidence_cache(fingerprint,claim,result_json,sources_json,created_at,expires_at,last_hit_at,hit_count)
      VALUES(?,?,?,?,?,?,NULL,0) ON CONFLICT(fingerprint) DO UPDATE SET claim=excluded.claim,
      result_json=excluded.result_json,sources_json=excluded.sources_json,created_at=excluded.created_at,
      expires_at=excluded.expires_at,last_hit_at=NULL,hit_count=0""",
      (key, claim[:MAX_CLAIM_CHARS], json.dumps(safe_result, ensure_ascii=False)[:1000000],
       json.dumps(sources, ensure_ascii=False), _iso(now), _iso(now + timedelta(seconds=ttl))))
    conn.commit()
    conn.close()

def get_cached_analysis(claim: str) -> dict[str, Any] | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM evidence_cache WHERE fingerprint=?", (fingerprint(claim),)).fetchone()
    if not row:
        conn.close()
        return None
    now = utc_now()
    expires = datetime.fromisoformat(row["expires_at"])
    created = datetime.fromisoformat(row["created_at"])
    fresh = expires > now
    conn.execute("UPDATE evidence_cache SET last_hit_at=?,hit_count=hit_count+1 WHERE fingerprint=?",
                 (_iso(now), row["fingerprint"]))
    conn.commit()
    conn.close()
    return {"fresh": fresh, "claim": row["claim"], "result": json.loads(row["result_json"]) if fresh else None,
            "sources": json.loads(row["sources_json"]), "created_at": row["created_at"],
            "expires_at": row["expires_at"], "age_seconds": max(0, int((now-created).total_seconds())),
            "hit_count": int(row["hit_count"]) + 1,
            "requires_revalidation": not fresh}

def list_investigations(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _conn()
    prefs = conn.execute("SELECT enabled,retention_days FROM memory_preferences WHERE session_id=?", (session_id,)).fetchone()
    if prefs and not prefs["enabled"]:
        conn.close()
        return []
    days = int(prefs["retention_days"]) if prefs else 90
    cutoff = _iso(utc_now() - timedelta(days=days))
    rows = conn.execute("""SELECT id,claim,verdict,score,status,created_at,updated_at,last_verified_at
      FROM investigations WHERE session_id=? AND updated_at>=? ORDER BY updated_at DESC LIMIT ?""",
      (session_id, cutoff, max(1, min(int(limit), 100)))).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_investigation(session_id: str, investigation_id: str) -> dict[str, Any] | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM investigations WHERE id=? AND session_id=?", (investigation_id, session_id)).fetchone()
    if not row:
        conn.close()
        return None
    events = conn.execute("SELECT event_type,payload_json,created_at FROM investigation_events WHERE investigation_id=? ORDER BY id",
                          (investigation_id,)).fetchall()
    relations = conn.execute("""SELECT r.relation,r.similarity,i.id,i.claim,i.verdict,i.updated_at
      FROM claim_relationships r JOIN investigations i ON i.id=CASE WHEN r.left_id=? THEN r.right_id ELSE r.left_id END
      WHERE r.left_id=? OR r.right_id=?""", (investigation_id, investigation_id, investigation_id)).fetchall()
    conn.close()
    data = dict(row)
    data["events"] = [{**dict(e), "payload": json.loads(e["payload_json"])} for e in events]
    data["related"] = [dict(r) for r in relations]
    return data

def record_event(session_id: str, investigation_id: str, event_type: str, payload: dict[str, Any]) -> bool:
    allowed = {"note", "evidence_added", "question_opened", "question_resolved", "revalidation"}
    if event_type not in allowed:
        raise ValueError("unsupported event_type")
    conn = _conn()
    owns = conn.execute("SELECT 1 FROM investigations WHERE id=? AND session_id=?", (investigation_id, session_id)).fetchone()
    if not owns:
        conn.close()
        return False
    _event(conn, investigation_id, event_type, payload)
    conn.execute("UPDATE investigations SET updated_at=? WHERE id=?", (_iso(), investigation_id))
    conn.commit()
    conn.close()
    return True

def add_claim_alias(session_id: str, investigation_id: str, alias_text: str, language: str | None = None) -> dict[str, Any]:
    alias = normalize_claim(alias_text)
    if len(alias) < 4:
        raise ValueError("alias must contain at least 4 normalized characters")
    if language is not None and (not isinstance(language, str) or len(language) > 40):
        raise ValueError("language must be a string of at most 40 characters")
    conn = _conn()
    owner = conn.execute("SELECT 1 FROM investigations WHERE id=? AND session_id=?", (investigation_id, session_id)).fetchone()
    if not owner:
        conn.close()
        raise LookupError("investigation not found")
    conn.execute("""INSERT OR IGNORE INTO claim_aliases(investigation_id,session_id,alias_text,alias_fingerprint,language,created_at)
      VALUES(?,?,?,?,?,?)""", (investigation_id, session_id, alias_text[:MAX_CLAIM_CHARS],
      fingerprint(alias_text), language, _iso()))
    conn.commit()
    row = conn.execute("SELECT id,alias_text,language,created_at FROM claim_aliases WHERE investigation_id=? AND alias_fingerprint=?",
                       (investigation_id, fingerprint(alias_text))).fetchone()
    conn.close()
    return dict(row) if row else {"saved": True}

def find_alias_matches(session_id: str, claim: str, limit: int = 8) -> list[dict[str, Any]]:
    key = fingerprint(claim)
    conn = _conn()
    rows = conn.execute("""SELECT a.investigation_id,a.alias_text,a.language,a.created_at,
      i.claim,i.verdict,i.updated_at FROM claim_aliases a
      JOIN investigations i ON i.id=a.investigation_id
      WHERE a.session_id=? AND a.alias_fingerprint=? ORDER BY a.created_at DESC LIMIT ?""",
      (session_id, key, max(1, min(int(limit), 20)))).fetchall()
    conn.close()
    return [{**dict(row), "relation": "cross_language_alias", "similarity": 1.0} for row in rows]

def revalidation_candidates(limit: int = 100) -> list[dict[str, Any]]:
    """Return expired shared cache entries for an external scheduler; never silently refresh."""
    conn = _conn()
    rows = conn.execute("""SELECT fingerprint,claim,created_at,expires_at FROM evidence_cache
      WHERE expires_at<=? ORDER BY expires_at LIMIT ?""", (_iso(), max(1, min(int(limit), 500)))).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def cleanup_expired() -> dict[str, int]:
    now = _iso()
    conn = _conn()
    expired = conn.execute("DELETE FROM evidence_cache WHERE expires_at<=?", (now,)).rowcount
    conn.execute("DELETE FROM investigations WHERE updated_at < ?", (_iso(utc_now()-timedelta(days=365)),))
    conn.commit()
    conn.close()
    return {"expired_cache_entries_removed": expired}
