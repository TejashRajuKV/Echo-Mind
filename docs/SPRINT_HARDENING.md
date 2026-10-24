# Echo Mind engineering sprint: hardening and verification

## What changed

- Shareable reports escape untrusted claim, explanation, and publisher text; external links are limited to absolute HTTP(S) URLs; JSON-LD escapes angle brackets before embedding in a script element.
- Frontend result, document-analysis, subscription, and modal HTML passes through the sanitizer before DOM insertion. Keep all API-provided strings treated as untrusted.
- Verdict reconciliation is evidence-first: model output cannot override conflict or insufficient independent evidence.
- Consensus now abstains when fewer than two independent publishers provide directional evidence. Known syndicated copies sharing a cluster count as one origin.
- Request validation covers malformed JSON shapes, type/length bounds, monitor score/evidence counts, correction URL schemes, and generic server errors.
- Rate-limit counters are stored in SQLite and shared between worker processes using the same local database. For multiple containers/hosts, configure a shared gateway or Redis-backed limiter; local SQLite is not a distributed rate limiter.
- Added a labelled regression fixture, unit/API tests, and GitHub Actions checks for Python compilation, JavaScript syntax, and deterministic tests.
- Added the `/monitor/notifications` endpoint and a standalone scheduled worker (`python monitor_worker.py`) to re-check opted-in claims and deliver pending notifications by SMTP.

## Run checks locally

```bash
python -m pip install flask flask-cors python-dotenv requests schedule
node --check script.js
python -m compileall -q app.py analysis_engine.py evidence_engine.py verification_engine.py verdict_policy.py shareable_report.py claim_monitor.py monitor_worker.py
python -m unittest discover -s tests -v
```

The tests intentionally do not call live search APIs, Vertex AI, Gemini, or SMTP. They verify deterministic policy and API behavior only. They are not a substitute for a separately run live integration test with configured API credentials.

## Enable scheduled monitoring

Run the worker as a separate long-lived process/container, not in every Flask worker:

```bash
MONITOR_INTERVAL_MINUTES=30 MONITOR_BATCH_SIZE=50 python monitor_worker.py
```

SMTP settings (all optional; without them, alerts remain in the in-app notification table):

- `SMTP_HOST`
- `SMTP_PORT` (default 587)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM` (defaults to the username)
- `SMTP_STARTTLS=true` (default)

Only run one scheduler instance against a given SQLite database unless you add a distributed lease/queue. For production deployments with multiple replicas, use a shared database, shared rate limiter, and a single scheduler/queue worker. Email is best-effort: failed deliveries remain pending and are retried on a later cycle.

## Evaluation dataset

`tests/fixtures/labelled_claims.json` is a small policy regression fixture, not a gold-standard accuracy benchmark. Before publishing precision/recall or accuracy claims, expand it with independently reviewed, dated claims, primary citations, adjudicated labels, and a documented train/test split. The automated tests assert safe abstention and conflict behavior rather than claim-level factual accuracy.
