import os
import json
import time
import hashlib
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ID = os.environ.get("PROJECT_ID", "echo-mind-472808")
LOCATION   = os.environ.get("LOCATION", "us-central1")

# API key is required – no hardcoded fallback
API_KEY = os.environ.get("ECHO_MIND_API_KEY")

# CORS – restrict to the deployed frontend origin plus localhost for dev.
# Set ALLOWED_ORIGINS=https://your-domain.com in .env for production.
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

MAX_REQUESTS_PER_HOUR = max(1, int(os.environ.get("MAX_REQUESTS_PER_HOUR", 100)))
MAX_CLAIM_LENGTH      = max(1, int(os.environ.get("MAX_CLAIM_LENGTH", 2000)))
DEBUG_MODE            = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
# Never permit the interactive debugger in managed/explicit production deployments.
if os.environ.get("K_SERVICE") or os.environ.get("FLASK_ENV", "").lower() == "production":
    DEBUG_MODE = False

# ---------------------------------------------------------------------------
# Persistent user-session database (SQLite, thread-safe)
# ---------------------------------------------------------------------------
SESSION_DB_PATH = Path(__file__).parent / "sessions.db"
_session_lock   = threading.Lock()


def _session_db():
    """Return a connection to the per-request sessions database."""
    conn = sqlite3.connect(SESSION_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            points      INTEGER NOT NULL DEFAULT 0,
            badges      TEXT    NOT NULL DEFAULT '[]',
            claim_count INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claim_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            claim       TEXT    NOT NULL,
            verdict     TEXT    NOT NULL,
            score       REAL,
            category    TEXT,
            analyzed_at TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
        )
    """)
    conn.commit()
    return conn


def get_or_create_session(session_id: str) -> dict:
    """Return the persisted session record, creating one if missing."""
    now = datetime.utcnow().isoformat()
    with _session_lock:
        conn = _session_db()
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO user_sessions VALUES (?, 0, '[]', 0, ?, ?)",
                (session_id, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        conn.close()
    return dict(row)


def update_session(session_id: str, points: int, badges: list, claim_text: str,
                   verdict: str, score, category: str):
    """Persist updated gamification state and append claim history."""
    now = datetime.utcnow().isoformat()
    with _session_lock:
        conn = _session_db()
        conn.execute(
            """UPDATE user_sessions
               SET points=?, badges=?, claim_count=claim_count+1, updated_at=?
               WHERE session_id=?""",
            (points, json.dumps(badges), now, session_id),
        )
        conn.execute(
            """INSERT INTO claim_history (session_id, claim, verdict, score, category, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, claim_text[:500], verdict, score, category, now),
        )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# In-process rate-limiter (keyed by IP + hour bucket)
# ---------------------------------------------------------------------------
_rate_counts: dict = {}
_rate_lock = threading.Lock()


def _check_rate_limit(ip: str) -> bool:
    bucket = f"{ip}_{int(time.time() // 3600)}"
    with _rate_lock:
        count = _rate_counts.get(bucket, 0) + 1
        _rate_counts[bucket] = count
        # Prune old buckets to avoid unbounded growth
        if len(_rate_counts) > 10_000:
            oldest = sorted(_rate_counts.keys())[:5_000]
            for k in oldest:
                del _rate_counts[k]
    return count <= MAX_REQUESTS_PER_HOUR


# ---------------------------------------------------------------------------
# Analysis engine import
# ---------------------------------------------------------------------------
try:
    from analysis_engine import analyze_claim
except ImportError:
    raise RuntimeError("Could not import 'analyze_claim'. Ensure analysis_engine.py is present.")

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", str(1024 * 1024)))

# Restrictive CORS: only allow declared origins, only the needed methods/headers
CORS(
    app,
    origins=ALLOWED_ORIGINS,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Session-ID"],
    supports_credentials=False,
    max_age=600,
)


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------
def rate_limited(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _check_rate_limit(request.remote_addr or "unknown"): 
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": f"Maximum {MAX_REQUESTS_PER_HOUR} requests per hour per IP.",
            }), 429
        return f(*args, **kwargs)
    return wrapper


def require_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            return jsonify({
                "error": "server_misconfigured",
                "message": "ECHO_MIND_API_KEY is not set on the server.",
            }), 500
        provided = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not provided or provided != API_KEY:
            return jsonify({
                "error": "unauthorized",
                "message": "Invalid or missing API key.",
            }), 401
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _derive_session_id() -> str:
    """
    Derive a stable, anonymous session id from the request.
    Prefer an explicit X-Session-ID header sent by the client (a UUID stored
    in localStorage), otherwise fall back to a hash of the IP.
    """
    explicit = request.headers.get("X-Session-ID", "").strip()
    if explicit and 16 <= len(explicit) <= 128:
        # Hash so that raw UUIDs are never stored verbatim
        return hashlib.sha256(explicit.encode()).hexdigest()
    # Fallback: derive from IP (coarse – all users behind same NAT share state)
    return hashlib.sha256((request.remote_addr or "unknown").encode()).hexdigest()


def _validate_claim(data) -> tuple[str | None, str | None]:
    """Return (claim_text, error_message)."""
    if not data or not isinstance(data, dict):
        return None, "Request body must be a JSON object."
    claim = data.get("claim")
    if not claim or not isinstance(claim, str):
        return None, "'claim' must be a non-empty string."
    claim = claim.strip()
    if not claim:
        return None, "'claim' must not be blank."
    if len(claim) > MAX_CLAIM_LENGTH:
        return None, f"'claim' exceeds maximum length of {MAX_CLAIM_LENGTH} characters."
    return claim, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/analyze", methods=["POST"])
@rate_limited
def analyze():
    """
    Public fact-checking endpoint.
    Each caller is identified by an anonymous session-id so gamification
    progress is isolated per user rather than shared globally.
    """
    data = request.get_json(silent=True)
    claim, err = _validate_claim(data)
    if err:
        return jsonify({"error": "bad_request", "message": err}), 400

    session_id = _derive_session_id()
    session    = get_or_create_session(session_id)

    current_points = session["points"]
    current_badges = json.loads(session["badges"])

    try:
        result = analyze_claim(claim, current_points, current_badges)
    except Exception:
        app.logger.exception("Claim analysis failed")
        return jsonify({"error": "analysis_failed", "message": "Claim analysis failed. Please retry later."}), 503
    if not isinstance(result, dict):
        app.logger.error("Analysis engine returned a non-object result")
        return jsonify({"error": "analysis_failed", "message": "Analysis returned an invalid result."}), 503

    # Persist updated state
    new_points = result.get("gamification", {}).get("points", current_points)
    new_badges = result.get("gamification", {}).get("badges", current_badges)
    verdict    = result.get("classification", "Unknown")
    score      = result.get("score", None)
    category   = result.get("personalization", {}).get("category", "general")

    update_session(session_id, new_points, new_badges, claim, verdict, score, category)

    # Annotate with session metadata (never expose raw session_id to client)
    result["session"] = {
        "claim_count": session["claim_count"] + 1,
        "points":      new_points,
        "badges":      new_badges,
    }

    return jsonify(result)


@app.route("/evolution", methods=["GET"])
@rate_limited
def claim_evolution_endpoint():
    """Returns chronological mutation and verdict drift history for a claim."""
    claim = request.args.get("claim", "").strip()
    if not claim:
        return jsonify({"error": "bad_request", "message": "'claim' query parameter required."}), 400
    try:
        from claim_evolution import get_claim_evolution_timeline
        return jsonify(get_claim_evolution_timeline(claim))
    except Exception:
        app.logger.exception("Claim evolution lookup failed")
        return jsonify({"error": "server_error", "message": "Could not load claim evolution."}), 500


@app.route("/document/analyze", methods=["POST"])
@rate_limited
def document_analysis_endpoint():
    """Extracts claims from research papers, official notices, and reports with passage citations."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    doc_text = data.get("text", "")
    doc_title = data.get("title", "Submitted Document")
    if not isinstance(doc_text, str) or not isinstance(doc_title, str):
        return jsonify({"error": "bad_request", "message": "Fields 'text' and 'title' must be strings."}), 400
    doc_text = doc_text.strip()
    doc_title = doc_title.strip() or "Submitted Document"
    if not doc_text:
        return jsonify({"error": "bad_request", "message": "'text' field required with document content."}), 400
    if len(doc_text) > 30000:
        return jsonify({"error": "bad_request", "message": "Document exceeds maximum size of 30,000 characters."}), 400
    try:
        from document_analysis import analyze_document_content
        result = analyze_document_content(doc_text, doc_title, verify_claims=True)
        return jsonify(result)
    except Exception:
        app.logger.exception("Document analysis failed")
        return jsonify({"error": "server_error", "message": "Document analysis failed."}), 500


@app.route("/monitor/subscribe", methods=["POST"])
@rate_limited
def monitor_subscribe_endpoint():
    """Subscribes caller to receive updates when significant new evidence or corrections emerge."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    claim = data.get("claim", "")
    verdict = data.get("verdict", "Unknown")
    email = data.get("email", "")
    try:
        score = int(data.get("score", 50))
        evidence_count = int(data.get("evidence_count", 0))
    except (TypeError, ValueError, OverflowError):
        return jsonify({"error": "bad_request", "message": "score and evidence_count must be integers."}), 400
    if not isinstance(claim, str) or not isinstance(verdict, str) or not isinstance(email, str):
        return jsonify({"error": "bad_request", "message": "claim, verdict, and email must be strings."}), 400
    claim, verdict, email = claim.strip(), verdict.strip() or "Unknown", email.strip()
    if len(claim) > MAX_CLAIM_LENGTH or not 0 <= score <= 100 or not 0 <= evidence_count <= 1000:
        return jsonify({"error": "bad_request", "message": "Claim, score, or evidence_count is outside the accepted range."}), 400
    if email and (len(email) > 254 or "@" not in email or any(ch.isspace() for ch in email)):
        return jsonify({"error": "bad_request", "message": "email must be a valid email address or blank."}), 400
    if not claim:
        return jsonify({"error": "bad_request", "message": "'claim' field required."}), 400

    session_id = _derive_session_id()
    try:
        from claim_monitor import subscribe_to_claim
        res = subscribe_to_claim(session_id, claim, verdict, score, evidence_count, email)
        return jsonify(res)
    except Exception as exc:
        app.logger.exception("Claim monitor subscription failed")
        return jsonify({"error": "server_error", "message": "Could not create monitor subscription."}), 500


@app.route("/monitor/list", methods=["GET"])
@rate_limited
def monitor_list_endpoint():
    """Returns active monitored claims for the current user session."""
    session_id = _derive_session_id()
    try:
        from claim_monitor import list_user_monitors
        return jsonify({"monitors": list_user_monitors(session_id)})
    except Exception as exc:
        return jsonify({"error": "server_error", "message": str(exc)}), 500


@app.route("/monitor/notifications", methods=["GET"])
@rate_limited
def monitor_notifications_endpoint():
    """Return recent in-app evidence alerts scoped to the caller's anonymous session."""
    session_id = _derive_session_id()
    try:
        from claim_monitor import list_user_notifications
        return jsonify({"notifications": list_user_notifications(session_id)})
    except Exception:
        app.logger.exception("Could not load monitor notifications")
        return jsonify({"error": "server_error", "message": "Could not load notifications."}), 500


@app.route("/report", methods=["GET"])
def shareable_report_endpoint():
    """Renders a standalone, printable, linkable HTML evidence report with ClaimReview schema."""
    claim = request.args.get("claim", "").strip()
    if not claim:
        return "<h3>Please provide a 'claim' parameter to generate a report.</h3>", 400
    if len(claim) > MAX_CLAIM_LENGTH:
        return "<h3>Claim exceeds the maximum accepted length.</h3>", 400
    try:
        from analysis_engine import analyze_claim
        from shareable_report import generate_shareable_report_html
        result = analyze_claim(claim, save_to_database=False)
        html = generate_shareable_report_html(result, claim)
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception:
        app.logger.exception("Shareable report generation failed")
        return "<h3>Report generation failed. Please retry later.</h3>", 500


@app.route("/transparency", methods=["GET"])
def transparency_endpoint():
    """Returns public quality and transparency metrics (citation coverage, latency, conflict rates)."""
    try:
        from transparency_dashboard import get_transparency_metrics
        return jsonify(get_transparency_metrics())
    except Exception as exc:
        return jsonify({"error": "server_error", "message": str(exc)}), 500


@app.route("/correction", methods=["POST"])
@rate_limited
def submit_correction_endpoint():
    """Accepts a human correction submission with primary evidence URL."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    fields = ("claim_text", "reported_verdict", "suggested_verdict", "evidence_url", "rationale", "contact_email")
    if any(key in data and not isinstance(data[key], str) for key in fields):
        return jsonify({"error": "bad_request", "message": "Correction fields must be strings."}), 400
    claim_text = data.get("claim_text", "").strip()
    reported_verdict = data.get("reported_verdict", "").strip()
    suggested_verdict = data.get("suggested_verdict", "").strip()
    evidence_url = data.get("evidence_url", "").strip()
    rationale = data.get("rationale", "").strip()
    contact_email = data.get("contact_email", "").strip()
    if len(claim_text) > MAX_CLAIM_LENGTH or len(rationale) > 10000 or len(evidence_url) > 2048 or len(contact_email) > 254:
        return jsonify({"error": "bad_request", "message": "One or more correction fields exceed the maximum length."}), 400
    from urllib.parse import urlparse
    parsed_evidence_url = urlparse(evidence_url)
    if parsed_evidence_url.scheme not in ("http", "https") or not parsed_evidence_url.netloc:
        return jsonify({"error": "bad_request", "message": "evidence_url must be an absolute HTTP or HTTPS URL."}), 400

    if not claim_text or not evidence_url or not rationale:
        return jsonify({"error": "bad_request", "message": "Fields 'claim_text', 'evidence_url', and 'rationale' are required."}), 400

    try:
        from transparency_dashboard import submit_human_correction
        res = submit_human_correction(
            claim_text=claim_text,
            reported_verdict=reported_verdict,
            suggested_verdict=suggested_verdict,
            evidence_url=evidence_url,
            rationale=rationale,
            contact_email=contact_email
        )
        return jsonify(res)
    except Exception:
        app.logger.exception("Correction submission failed")
        return jsonify({"error": "server_error", "message": "Correction submission failed."}), 500


@app.route("/history", methods=["GET"])
@rate_limited
def history():
    """
    Return the caller's recent claim history (last 20 entries).
    Scoped to the anonymous session derived from their request.
    """
    session_id = _derive_session_id()
    with _session_lock:
        conn = _session_db()
        rows = conn.execute(
            """SELECT claim, verdict, score, category, analyzed_at
               FROM claim_history
               WHERE session_id = ?
               ORDER BY analyzed_at DESC LIMIT 20""",
            (session_id,),
        ).fetchall()
        conn.close()
    return jsonify({"history": [dict(r) for r in rows]})


@app.route("/stats", methods=["GET"])
@require_api_key
@rate_limited
def get_database_stats():
    """Admin endpoint – returns fact-check database statistics."""
    try:
        from database_helper import get_database_stats as _stats
        return jsonify({"status": "success", "data": _stats()})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Public health-check – no authentication required."""
    return jsonify({
        "status":  "healthy",
        "service": "Echo Mind AI Fact Checker",
        "time":    datetime.utcnow().isoformat() + "Z",
        "endpoints": {
            "/analyze":             "POST – AI fact-checking (rate-limited, session-scoped)",
            "/history":             "GET  – Caller's claim history (session-scoped)",
            "/evolution":           "GET  – Claim mutation timeline & verdict drift",
            "/document/analyze":    "POST – Research document/notice chunking & passage citations",
            "/monitor/subscribe":   "POST – Opt-in alert subscription on new evidence",
            "/monitor/list":        "GET  – List active monitors for user session",
            "/monitor/notifications": "GET – List session-scoped monitor notifications",
            "/report":              "GET  – Linkable HTML evidence report with ClaimReview schema",
            "/transparency":        "GET  – Quality observability metrics & audit benchmarks",
            "/correction":          "POST – Submit human correction with citation evidence",
            "/stats":               "GET  – DB statistics (requires X-API-Key)",
            "/health":              "GET  – Health check (public)",
        },
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialise the fact-check database with sample data if empty
    try:
        from database_helper import get_database_stats, initialize_sample_data
        if get_database_stats().get("total_claims", 0) == 0:
            print("[INIT] Initialising database with sample data...")
            initialize_sample_data()
    except Exception as exc:
        print(f"[WARN] Database initialisation warning: {exc}")

    port = int(os.environ.get("PORT", 8080))
    print(f"[START] Echo Mind running on port {port} (debug={DEBUG_MODE})")
    # debug=False in production; controlled strictly through env var FLASK_DEBUG
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)
