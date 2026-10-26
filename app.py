import os
import json
import time
import hashlib
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
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
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080,https://tejashrajukv.github.io",
)
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_buckets (
            bucket_key TEXT NOT NULL,
            hour_bucket INTEGER NOT NULL,
            request_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (bucket_key, hour_bucket)
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


# Legacy test-hook kept for existing test fixtures; counters are stored in SQLite now.
_rate_counts: dict = {}


# ---------------------------------------------------------------------------
# SQLite-backed rate limiter shared across worker processes on one host.
# For multi-instance deployments, use a shared gateway/Redis rate limiter.
# ---------------------------------------------------------------------------
def _check_rate_limit(ip: str) -> bool:
    hour_bucket = int(time.time() // 3600)
    bucket_key = hashlib.sha256((ip or "unknown").encode("utf-8")).hexdigest()
    conn = _session_db()
    try:
        # IMMEDIATE serializes concurrent increments across workers sharing this DB.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO rate_limit_buckets(bucket_key, hour_bucket, request_count) VALUES (?, ?, 1) "
            "ON CONFLICT(bucket_key, hour_bucket) DO UPDATE SET request_count=request_count+1",
            (bucket_key, hour_bucket),
        )
        row = conn.execute(
            "SELECT request_count FROM rate_limit_buckets WHERE bucket_key=? AND hour_bucket=?",
            (bucket_key, hour_bucket),
        ).fetchone()
        conn.execute("DELETE FROM rate_limit_buckets WHERE hour_bucket < ?", (hour_bucket - 2,))
        conn.commit()
        return int(row["request_count"]) <= MAX_REQUESTS_PER_HOUR
    except Exception:
        conn.rollback()
        # Fail closed if the persistent limiter cannot be updated.
        app.logger.exception("Rate limiter storage failed")
        return False
    finally:
        conn.close()


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
        provided = request.headers.get("X-API-Key")
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
@app.route("/")
def serve_frontend():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.route("/<path:asset_path>")
def serve_frontend_assets(asset_path):
    # Limit static serving to the project's public UI assets.
    if asset_path in {"styles.css", "script.js"}:
        return send_from_directory(Path(__file__).parent, asset_path)
    if asset_path in {"assets/logo.svg", "assets/echo-evidence-collage.webp"}:
        return send_from_directory(Path(__file__).parent, asset_path)
    return jsonify({"error": "not_found"}), 404


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

    # Memory is a continuity aid, not evidence. Exact fresh matches may reuse cached analysis.
    try:
        from context_memory import prepare_context, record_investigation
        context_snapshot = prepare_context(session_id, claim)
    except Exception:
        app.logger.exception("Context memory lookup failed; continuing with fresh analysis")
        context_snapshot = {"mode": "fresh", "matches": [], "cache": None, "memory_enabled": False}

    try:
        cached = context_snapshot.get("cache")
        if context_snapshot.get("mode") == "exact_cache" and cached and cached.get("fresh") and isinstance(cached.get("result"), dict):
            result = dict(cached["result"])
            result["cache_metadata"] = {
                "hit": True, "age_seconds": cached.get("age_seconds"),
                "created_at": cached.get("created_at"), "expires_at": cached.get("expires_at"),
                "source_count": len(cached.get("sources", [])),
                "note": "Exact-claim analysis reused while fresh; expired claims require revalidation."
            }
        else:
            result = analyze_claim(claim, current_points, current_badges)
            result["cache_metadata"] = {
                "hit": False, "mode": context_snapshot.get("mode", "fresh"),
                "related_investigations": [
                    {"claim": item.get("claim"), "verdict": item.get("verdict"),
                     "similarity": item.get("similarity"), "relation": item.get("relation"),
                     "updated_at": item.get("updated_at")}
                    for item in context_snapshot.get("matches", [])
                ],
                "note": "Related history is contextual only, not evidence; material differences require fresh verification."
            }
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

    try:
        from context_memory import record_investigation
        investigation = record_investigation(session_id, claim, result, context_snapshot.get("matches", []))
        result["investigation"] = investigation
    except Exception:
        app.logger.exception("Could not persist investigation memory")
        result["investigation"] = {"saved": False}

    # Annotate with session metadata (never expose raw session_id to client)
    result["session"] = {
        "claim_count": session["claim_count"] + 1,
        "points":      new_points,
        "badges":      new_badges,
    }

    return jsonify(result)


@app.route("/followup", methods=["POST"])
@rate_limited
def followup_question_endpoint():
    """Answer a question using the claim result and its retrieved citations."""
    if request.content_length and request.content_length > 24000:
        return jsonify({"error": "bad_request", "message": "Follow-up context is too large."}), 413

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400

    claim = data.get("claim", "")
    question = data.get("question", "")
    classification = data.get("classification", "Unknown")
    explanation = data.get("explanation", "")
    sources = data.get("evidence_sources", [])
    score = data.get("score")
    if not all(isinstance(value, str) for value in (claim, question, classification, explanation)):
        return jsonify({"error": "bad_request", "message": "Claim, question, verdict, and explanation must be text."}), 400
    claim, question = claim.strip(), question.strip()
    if not claim or len(claim) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "Claim is empty or exceeds the allowed length."}), 400
    if not question or len(question) > 1200:
        return jsonify({"error": "bad_request", "message": "Enter a question up to 1,200 characters."}), 400
    if not isinstance(sources, list) or len(sources) > 8 or any(not isinstance(source, dict) for source in sources):
        return jsonify({"error": "bad_request", "message": "Evidence sources must be a list of up to 8 records."}), 400

    try:
        from analysis_engine import answer_followup_question
        answer = answer_followup_question(claim, question, {
            "classification": classification[:80],
            "score": score if isinstance(score, (int, float)) else None,
            "explanation": explanation[:1800],
            "evidence_sources": sources,
        })
        return jsonify(answer)
    except Exception as exc:
        print(f"[WARN] Follow-up answer error: {exc}")
        return jsonify({"error": "server_error", "message": "Could not answer from this check right now."}), 500


@app.route("/evolution", methods=["GET"])
@rate_limited
def claim_evolution_endpoint():
    """Returns chronological mutation and verdict drift history for a claim."""
    claim = request.args.get("claim", "").strip()
    if not claim:
        return jsonify({"error": "bad_request", "message": "'claim' query parameter required."}), 400
    if len(claim) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "Claim exceeds maximum accepted length."}), 400
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
    if len(doc_title) > 200:
        return jsonify({"error": "bad_request", "message": "Document title must be 200 characters or fewer."}), 400
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
    if len(claim_text) > MAX_CLAIM_LENGTH or len(rationale) > 5000 or len(evidence_url) > 2048 or len(contact_email) > 254:
        return jsonify({"error": "bad_request", "message": "One or more correction fields exceed the maximum length."}), 400
    if contact_email and ("@" not in contact_email or any(ch.isspace() for ch in contact_email)):
        return jsonify({"error": "bad_request", "message": "contact_email must be a valid email address or blank."}), 400
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
            "/context/revalidate": "POST – Revalidate expired source-backed cache (API key)",
            "/context/revalidation-history": "GET – Revalidation/verdict-change history (API key)",
            "/claim-family/compare": "POST – Compare related claims and material changes",
            "/claim-family/evaluation": "GET – Labelled claim-family benchmark (API key)",
            "/investigations/<id>/provenance": "GET/POST – Claim-to-source provenance graph",
            "/message/ocr": "POST – Optional local OCR for uploaded images",
            "/message/language": "POST – Best-effort language detection",
            "/public/fact-check": "GET – Generate a public standalone fact-check page",
            "/review/corrections": "GET – Correction review queue (API key)",
            "/notifications": "GET/POST – Session-scoped in-app notifications",
        },
    })



# ---------------------------------------------------------------------------
# Context memory, incremental verification, and investigation workspace
# ---------------------------------------------------------------------------
@app.route("/context/prepare", methods=["POST"])
@rate_limited
def context_prepare_endpoint():
    data = request.get_json(silent=True)
    claim, err = _validate_claim(data)
    if err:
        return jsonify({"error": "bad_request", "message": err}), 400
    try:
        from context_memory import prepare_context
        context = prepare_context(_derive_session_id(), claim)
        if context.get("cache"):
            context["cache"] = {k: v for k, v in context["cache"].items() if k != "result"}
        return jsonify(context)
    except Exception:
        app.logger.exception("Context preparation failed")
        return jsonify({"error": "server_error", "message": "Could not prepare investigation context."}), 500


@app.route("/investigations", methods=["GET", "POST"])
@rate_limited
def investigations_endpoint():
    from context_memory import list_investigations, record_investigation, related_investigations
    session_id = _derive_session_id()
    if request.method == "GET":
        try:
            return jsonify({"investigations": list_investigations(session_id, request.args.get("limit", default=20, type=int))})
        except Exception:
            app.logger.exception("Investigation listing failed")
            return jsonify({"error": "server_error", "message": "Could not list investigations."}), 500
    data = request.get_json(silent=True)
    claim, err = _validate_claim(data)
    if err:
        return jsonify({"error": "bad_request", "message": err}), 400
    try:
        related = related_investigations(session_id, claim)
        item = record_investigation(session_id, claim, {"classification": "Not yet verified", "score": None, "sources": []}, related)
        return jsonify({"investigation": item, "related": related}), 201
    except Exception:
        app.logger.exception("Investigation creation failed")
        return jsonify({"error": "server_error", "message": "Could not create investigation."}), 500


@app.route("/investigations/<investigation_id>", methods=["GET", "DELETE"])
@rate_limited
def investigation_detail_endpoint(investigation_id):
    from context_memory import get_investigation, delete_investigation
    session_id = _derive_session_id()
    item = get_investigation(session_id, investigation_id)
    if not item:
        return jsonify({"error": "not_found", "message": "Investigation not found."}), 404
    if request.method == "DELETE":
        delete_investigation(session_id, investigation_id)
        return jsonify({"deleted": True, "id": investigation_id})
    return jsonify({"investigation": item})


@app.route("/investigations/<investigation_id>/events", methods=["POST"])
@rate_limited
def investigation_event_endpoint(investigation_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    event_type, payload = data.get("event_type", "note"), data.get("payload", {})
    if not isinstance(event_type, str) or not isinstance(payload, dict) or len(json.dumps(payload, ensure_ascii=False)) > 10000:
        return jsonify({"error": "bad_request", "message": "Invalid event type or payload."}), 400
    try:
        from context_memory import record_event
        if not record_event(_derive_session_id(), investigation_id, event_type, payload):
            return jsonify({"error": "not_found", "message": "Investigation not found."}), 404
        return jsonify({"saved": True})
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400
    except Exception:
        app.logger.exception("Investigation event write failed")
        return jsonify({"error": "server_error", "message": "Could not save investigation event."}), 500


@app.route("/memory/preferences", methods=["GET", "POST"])
@rate_limited
def memory_preferences_endpoint():
    from context_memory import get_preferences, set_preferences
    session_id = _derive_session_id()
    if request.method == "GET":
        return jsonify(get_preferences(session_id))
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    try:
        return jsonify(set_preferences(session_id, data.get("enabled", True), data.get("retention_days", 90)))
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400


@app.route("/memory/clear", methods=["DELETE"])
@rate_limited
def memory_clear_endpoint():
    from context_memory import clear_private_memory
    return jsonify({"deleted_investigations": clear_private_memory(_derive_session_id())})


@app.route("/context/cache/expired", methods=["GET"])
@require_api_key
@rate_limited
def expired_context_cache_endpoint():
    from context_memory import revalidation_candidates
    limit = request.args.get("limit", default=100, type=int)
    if limit < 1 or limit > 500:
        return jsonify({"error": "bad_request", "message": "limit must be between 1 and 500."}), 400
    try:
        return jsonify({"expired": revalidation_candidates(limit), "note": "Expired entries are listed but retained until a revalidation worker processes them."})
    except Exception:
        app.logger.exception("Expired cache inspection failed")
        return jsonify({"error": "server_error", "message": "Could not inspect expired cache."}), 500



@app.route("/investigations/<investigation_id>/aliases", methods=["POST"])
@rate_limited
def investigation_alias_endpoint(investigation_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    alias, language = data.get("alias"), data.get("language")
    if not isinstance(alias, str) or not alias.strip():
        return jsonify({"error": "bad_request", "message": "'alias' must be a non-empty string."}), 400
    if len(alias) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "Alias is too long."}), 400
    try:
        from context_memory import add_claim_alias
        item = add_claim_alias(_derive_session_id(), investigation_id, alias, language)
        return jsonify({"alias": item, "note": "Alias links claims for investigation continuity; it is not evidence of truth."}), 201
    except LookupError:
        return jsonify({"error": "not_found", "message": "Investigation not found."}), 404
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400
    except Exception:
        app.logger.exception("Claim alias registration failed")
        return jsonify({"error": "server_error", "message": "Could not register claim alias."}), 500


@app.route("/message/analyze", methods=["POST"])
@rate_limited
def forwarded_message_analysis_endpoint():
    """Analyze pasted/forwarded text or OCR text supplied by a client-side OCR step."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad_request", "message": "Request body must be a JSON object."}), 400
    text_value = data.get("text", data.get("ocr_text", ""))
    title = data.get("title", "Forwarded message")
    if not isinstance(text_value, str) or not isinstance(title, str):
        return jsonify({"error": "bad_request", "message": "text/ocr_text and title must be strings."}), 400
    text_value, title = text_value.strip(), title.strip()[:200] or "Forwarded message"
    if not text_value:
        return jsonify({"error": "bad_request", "message": "Provide message text or OCR-extracted text."}), 400
    if len(text_value) > 30000:
        return jsonify({"error": "bad_request", "message": "Message text exceeds 30,000 characters."}), 400
    try:
        from document_analysis import analyze_document_content
        result = analyze_document_content(text_value, title, verify_claims=True)
        result["input_metadata"] = {
            "kind": "forwarded_message_or_ocr_text",
            "ocr_performed_by_server": False,
            "note": "If this came from a screenshot, OCR text must be supplied by the client. Verify extracted text against the original image."
        }
        return jsonify(result)
    except Exception:
        app.logger.exception("Forwarded message analysis failed")
        return jsonify({"error": "server_error", "message": "Message analysis failed."}), 500



# ---------------------------------------------------------------------------
# Incremental verification, provenance, OCR and review APIs
# ---------------------------------------------------------------------------
@app.route("/context/revalidate", methods=["POST"])
@require_api_key
@rate_limited
def context_revalidate_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        limit = int(data.get("limit", 10))
    except (TypeError, ValueError):
        return jsonify({"error": "bad_request", "message": "limit must be an integer."}), 400
    if not 1 <= limit <= 100:
        return jsonify({"error": "bad_request", "message": "limit must be between 1 and 100."}), 400
    try:
        from incremental_verification import revalidate_expired
        return jsonify(revalidate_expired(limit))
    except Exception:
        app.logger.exception("Cache revalidation failed")
        return jsonify({"error": "server_error", "message": "Cache revalidation failed."}), 500


@app.route("/context/revalidation-history", methods=["GET"])
@require_api_key
@rate_limited
def context_revalidation_history_endpoint():
    claim = request.args.get("claim", "").strip()
    if not claim or len(claim) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "A valid claim query parameter is required."}), 400
    try:
        from incremental_verification import revalidation_history
        return jsonify({"claim": claim, "history": revalidation_history(claim)})
    except Exception:
        app.logger.exception("Revalidation history lookup failed")
        return jsonify({"error": "server_error", "message": "Could not load revalidation history."}), 500


@app.route("/claim-family/compare", methods=["POST"])
@rate_limited
def claim_family_compare_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("claim_a"), str) or not isinstance(data.get("claim_b"), str):
        return jsonify({"error": "bad_request", "message": "claim_a and claim_b must be strings."}), 400
    if not data["claim_a"].strip() or not data["claim_b"].strip() or max(len(data["claim_a"]), len(data["claim_b"])) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "Claims must be non-empty and within the length limit."}), 400
    try:
        from incremental_verification import claim_family_similarity
        return jsonify(claim_family_similarity(data["claim_a"], data["claim_b"]))
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400


@app.route("/claim-family/evaluation", methods=["GET"])
@require_api_key
@rate_limited
def claim_family_evaluation_endpoint():
    try:
        from incremental_verification import evaluate_claim_families
        return jsonify(evaluate_claim_families())
    except Exception:
        app.logger.exception("Claim-family evaluation failed")
        return jsonify({"error": "server_error", "message": "Could not evaluate claim families."}), 500


@app.route("/investigations/<investigation_id>/provenance", methods=["GET", "POST"])
@rate_limited
def investigation_provenance_endpoint(investigation_id):
    from context_memory import get_investigation
    session_id = _derive_session_id()
    item = get_investigation(session_id, investigation_id)
    if not item:
        return jsonify({"error": "not_found", "message": "Investigation not found."}), 404
    try:
        from incremental_verification import build_provenance_graph, get_provenance_graph
        if request.method == "GET":
            return jsonify(get_provenance_graph(investigation_id))
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("sources", []), list):
            return jsonify({"error": "bad_request", "message": "sources must be an array."}), 400
        if len(data.get("sources", [])) > 100:
            return jsonify({"error": "bad_request", "message": "At most 100 sources are accepted."}), 400
        graph = build_provenance_graph(investigation_id, item.get("claim", ""), data.get("sources", []))
        from context_memory import record_event
        record_event(session_id, investigation_id, "evidence_added", {"source_count": len(graph["edges"])})
        return jsonify(graph), 201
    except Exception:
        app.logger.exception("Provenance graph operation failed")
        return jsonify({"error": "server_error", "message": "Could not process provenance graph."}), 500


@app.route("/message/ocr", methods=["POST"])
@rate_limited
def message_ocr_endpoint():
    if "image" not in request.files:
        return jsonify({"error": "bad_request", "message": "Upload an image in the 'image' field."}), 400
    try:
        from ocr_support import extract_upload
        return jsonify(extract_upload(request.files["image"]))
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": "ocr_unavailable", "message": str(exc)}), 503
    except Exception:
        app.logger.exception("Image OCR failed")
        return jsonify({"error": "ocr_failed", "message": "Could not extract text from image."}), 422


@app.route("/message/language", methods=["POST"])
@rate_limited
def message_language_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return jsonify({"error": "bad_request", "message": "text must be a string."}), 400
    if not data["text"].strip() or len(data["text"]) > 30000:
        return jsonify({"error": "bad_request", "message": "text must be non-empty and at most 30,000 characters."}), 400
    from incremental_verification import detect_language
    return jsonify({"language": detect_language(data["text"]), "automatic_translation": False,
                    "note": "Language detection is a hint only. Verify claims against reliable sources in the original language."})


@app.route("/public/fact-check", methods=["GET"])
@rate_limited
def public_fact_check_endpoint():
    # A public report is generated from a fresh analysis and does not expose private investigation history.
    claim = request.args.get("claim", "").strip()
    if not claim or len(claim) > MAX_CLAIM_LENGTH:
        return jsonify({"error": "bad_request", "message": "A valid claim query parameter is required."}), 400
    try:
        from analysis_engine import analyze_claim
        from shareable_report import generate_shareable_report_html
        result = analyze_claim(claim, save_to_database=False)
        result["claim"] = claim
        page = generate_shareable_report_html(result, claim, report_id="public-" + __import__("hashlib").sha256(claim.encode()).hexdigest()[:16])
        return page, 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
    except Exception:
        app.logger.exception("Public fact-check page generation failed")
        return "<h3>Fact-check page could not be generated. Please retry later.</h3>", 500


@app.route("/review/corrections", methods=["GET"])
@require_api_key
@rate_limited
def correction_review_queue_endpoint():
    try:
        from transparency_dashboard import list_human_corrections
        status = request.args.get("status", "pending")
        limit = request.args.get("limit", default=100, type=int)
        return jsonify({"queue": list_human_corrections(status, limit),
                        "note": "Queue entries are user-submitted reports, not verified corrections. Review each linked source before changing status."})
    except Exception:
        app.logger.exception("Correction review queue failed")
        return jsonify({"error": "server_error", "message": "Could not load correction queue."}), 500


@app.route("/notifications", methods=["GET"])
@rate_limited
def notifications_endpoint():
    try:
        from notification_store import list_for_session
        return jsonify({"notifications": list_for_session(_derive_session_id())})
    except Exception:
        app.logger.exception("Notification listing failed")
        return jsonify({"error": "server_error", "message": "Could not load notifications."}), 500


@app.route("/notifications", methods=["POST"])
@rate_limited
def notification_create_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("title"), str) or not isinstance(data.get("body"), str):
        return jsonify({"error": "bad_request", "message": "title and body must be strings."}), 400
    if not data["title"].strip() or len(data["title"]) > 200 or len(data["body"]) > 4000:
        return jsonify({"error": "bad_request", "message": "title/body is empty or too long."}), 400
    try:
        from notification_store import create
        return jsonify(create(_derive_session_id(), data["title"], data["body"], data.get("kind", "info"), data.get("payload", {}))), 201
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400



@app.route("/message/multilingual-match", methods=["POST"])
@rate_limited
def multilingual_match_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return jsonify({"error": "bad_request", "message": "text must be a string."}), 400
    text_value = data["text"].strip()
    if not text_value or len(text_value) > 5000:
        return jsonify({"error": "bad_request", "message": "text must be non-empty and at most 5,000 characters."}), 400
    try:
        from incremental_verification import multilingual_match_candidates
        return jsonify(multilingual_match_candidates(_derive_session_id(), text_value))
    except Exception:
        app.logger.exception("Multilingual matching failed")
        return jsonify({"error": "server_error", "message": "Could not find related investigations."}), 500


@app.route("/review/corrections/<int:correction_id>", methods=["POST"])
@require_api_key
@rate_limited
def correction_review_update_endpoint(correction_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("status"), str):
        return jsonify({"error": "bad_request", "message": "status is required."}), 400
    note = data.get("reviewer_note", "")
    if not isinstance(note, str):
        return jsonify({"error": "bad_request", "message": "reviewer_note must be a string."}), 400
    try:
        from transparency_dashboard import review_human_correction
        result = review_human_correction(correction_id, data["status"], note)
        return (jsonify(result), 200) if result["updated"] else (jsonify({"error": "not_found", "message": "Correction not found."}), 404)
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400
    except Exception:
        app.logger.exception("Correction review update failed")
        return jsonify({"error": "server_error", "message": "Could not update correction review."}), 500


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@rate_limited
def notification_mark_read_endpoint(notification_id):
    from notification_store import mark_read
    if not mark_read(_derive_session_id(), notification_id):
        return jsonify({"error": "not_found", "message": "Notification not found."}), 404
    return jsonify({"read": True, "id": notification_id})

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
