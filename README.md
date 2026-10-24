# Thunderwing Falcons — Echo Mind AI Fact-Checker

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Pro-green.svg)
![Vertex AI](https://img.shields.io/badge/Vertex_AI-Google_Cloud-orange.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![License](https://img.shields.io/badge/License-Educational-blueviolet.svg)

> **Echo Mind** — *Suggesting intelligent responses and echoes of knowledge*  
> Built by **Thunderwing Falcons** for the Google Hackathon.

---

## Overview

Echo Mind is an evidence-first fact-checking prototype that **retrieves and audits evidence before model reasoning**. Evidence coverage depends on available API credentials, local data, and network access; source stance and authority signals are heuristic and every result needs human review.

The system can use Google Vertex AI (Gemini) when configured and has fallback paths for some failures. Full offline capability is not guaranteed because several retrieval connectors depend on external services.

---

## Feature Set

### Core Evidence & Verification Engine

| Feature | Description |
|---|---|
| **Evidence Intelligence Engine** | Queries Google Fact Check Tools API, FreeNewsAPI, and a local authoritative database *before* asking the AI. Every source gets a domain-authority tier score (0-100). |
| **Multi-Source Conflict Detection** | Decomposes every claim into atomic sub-claims and checks each independently across publishers. Detects consensus vs. active contradiction. |
| **Atomic Claim Decomposition** | Splits compound statements into individually verifiable factual assertions for granular accuracy. |
| **Echo-Chamber Deduplication** | Clusters syndicated wire reprints (PTI, AP, Reuters, ANI) and counts them as one source to prevent artificial consensus inflation. |
| **Explainable Credibility Scoring** | Multi-factor formula: Source Convergence + Domain Authority + Publisher Diversity. Shown as a transparent breakdown, not a black-box number. |
| **Gamified Critical Thinking** | Points, badges, and personalised tips per category. State is isolated per anonymous session -- not shared across users. |

### Intelligence Extensions

| Feature | Description |
|---|---|
| **Claim Evolution Tracker** | Links repeated mutations of the same claim across time, tracking wording changes, evidence accumulation, and verdict drift. Stored in `claim_evolution.db`. |
| **Indian-Language Verification** | Native script detection for Kannada, Hindi, Tamil, Telugu, and Bengali. Preserves original vernacular wording and queries regional trusted publishers (Prajavani, Vijayavani, Dainik Jagran, Amar Ujala, Eenadu, Dinamalar, Anandabazar Patrika). |
| **Research Document Analysis** | Paste any official notice, circular, research paper, or court order. The engine chunks paragraphs, extracts factual claims, and traces each to an estimated page and exact passage. |
| **Opt-In Claim Monitoring** | Store subscriptions and in-app alerts in SQLite. A separate worker must be running for scheduled checks; email delivery also requires SMTP configuration. |
| **Shareable Evidence Reports** | Generates a standalone HTML evidence report with full citations, verification date, methodology, and limitations. Includes Google **ClaimReview** Schema.org JSON-LD structured data for search engine eligibility. |
| **Quality & Transparency Dashboard** | Real-time telemetry: citation coverage %, retrieval success %, unresolved conflict %, average latency, benchmark accuracy, and open human correction queue. |

---

## Architecture

```
User Browser
    |
    +-- index.html + styles.css + script.js
    |       (file:// or via Flask static serving)
    |
    +-- HTTP --> Flask (app.py -- port 8080)
                    |
                    +-- /analyze --> analysis_engine.py
                    |                   +-- evidence_engine.py      (retrieve first)
                    |                   +-- verification_engine.py  (consensus + score)
                    |                   +-- indian_language_engine.py
                    |                   +-- claim_evolution.py
                    |                   +-- Vertex AI / Gemini 2.5 Pro  (reason over evidence)
                    |
                    +-- /evolution        --> claim_evolution.py
                    +-- /document/analyze --> document_analysis.py
                    +-- /monitor/*        --> claim_monitor.py
                    +-- /report           --> shareable_report.py
                    +-- /transparency     --> transparency_dashboard.py
                    +-- /correction       --> transparency_dashboard.py
```

### Databases (SQLite, local)

| File | Purpose |
|---|---|
| `factchecks.db` | Authoritative fact-checks + `analysis_logs` table (separate from fact-checks to prevent circular self-reference) |
| `sessions.db` | Per-user gamification points, badges, and claim history |
| `claim_evolution.db` | Claim variant clusters and mutation timelines |
| `claim_monitors.db` | Active opt-in monitor subscriptions and update records |
| `transparency_metrics.db` | Runtime telemetry and human correction queue |
| `context_memory.db` | Session-scoped investigations, related-claim links, explicit translated aliases, and source-backed cache entries with expiry |

---

## REST API

All endpoints are served by `app.py` on port `8080`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/analyze` | Session | AI fact-checking with full evidence pipeline |
| `GET` | `/evolution` | -- | Claim mutation timeline and verdict drift |
| `POST` | `/document/analyze` | -- | Research document chunking and passage citation |
| `POST` | `/monitor/subscribe` | Session | Opt-in alert subscription |
| `GET` | `/monitor/list` | Session | List active monitors for current session |
| `GET` | `/report` | -- | Linkable HTML evidence report + ClaimReview JSON-LD |
| `GET` | `/transparency` | -- | Quality observability metrics |
| `POST` | `/correction` | -- | Submit human correction with citation evidence |
| `GET` | `/history` | Session | Caller's recent claim history (last 20) |
| `GET` | `/stats` | API Key | Database statistics (admin) |
| `GET` | `/health` | -- | Service health check |
| `POST` | `/context/prepare` | Session | Exact-cache and related-investigation context; cache metadata only |
| `GET/POST` | `/investigations` | Session | List investigations or create an unverified workspace item |
| `GET/DELETE` | `/investigations/<id>` | Session | Read or delete an investigation owned by the current session |
| `POST` | `/investigations/<id>/events` | Session | Add a private note or investigation event |
| `POST` | `/investigations/<id>/aliases` | Session | Link an explicitly supplied translated/paraphrased claim |
| `GET/POST` | `/memory/preferences` | Session | Configure memory opt-out and retention |
| `DELETE` | `/memory/clear` | Session | Delete private investigation history |
| `POST` | `/message/analyze` | Session | Analyze pasted or client-provided OCR text from a forwarded message |
| `GET` | `/context/cache/expired` | API Key | Inspect expired cache entries for an external revalidation worker |

---

## Project Structure

```
Echo Mind/
+-- index.html                  # Frontend -- single-page app
+-- styles.css                  # Full design system (1,650+ lines)
+-- script.js                   # Frontend logic + all modal interactions
|
+-- app.py                      # Flask server -- all 11 routes
+-- analysis_engine.py          # Orchestrator -- evidence pipeline + Vertex AI
+-- context_memory.py           # Privacy-aware investigation memory + source-backed evidence cache
|
+-- evidence_engine.py          # Google Fact Check API + FreeNewsAPI + DB connector
+-- verification_engine.py      # Atomic sub-claim decomposition + consensus scoring
+-- claim_evolution.py          # Claim mutation tracker (SQLite)
+-- indian_language_engine.py   # Kannada/Hindi/Tamil/Telugu/Bengali support
+-- document_analysis.py        # PDF/notice text chunker + claim extractor
+-- claim_monitor.py            # Opt-in subscription + update detection
+-- shareable_report.py         # HTML report + ClaimReview Schema.org JSON-LD
+-- transparency_dashboard.py   # Telemetry logger + public metrics calculator
|
+-- database_helper.py          # factchecks.db and analysis_logs helpers
+-- auto_updater.py             # Daily news context refresh (BBC, Reuters, The Hindu)
+-- rag_integration.py          # RAG system integration layer
+-- rag_system.py               # Retrieval-Augmented Generation engine
|
+-- factchecks.db               # Authoritative fact-check database
+-- sessions.db                 # Per-user session and gamification state
+-- claim_evolution.db          # Claim variant clusters
+-- claim_monitors.db           # Active opt-in monitors
+-- transparency_metrics.db     # Runtime telemetry
+-- real_time_data.db           # Real-time sports and news data
|
+-- .env                        # Secret keys -- NOT committed to Git
+-- .env.example                # Template for required environment variables
+-- .gitignore                  # Excludes .env, __pycache__, *.db, logs
|
+-- requirements.txt            # Core Python dependencies
+-- requirements_rag.txt        # RAG-specific dependencies
+-- Dockerfile                  # Container definition for Cloud Run
+-- deploy_to_cloud_run.bat     # One-click Cloud Run deployment
|
+-- API_SETUP_GUIDE.md          # API key setup instructions
+-- AUTO_UPDATE_GUIDE.md        # Auto-updater configuration and scheduling
+-- RAG_SYSTEM_GUIDE.md         # RAG system setup and usage guide
|
+-- assets/                     # Logo and image assets
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip
- (Optional) Google Cloud SDK -- required only for Vertex AI / BigQuery; the system runs fully on its deterministic fallback engine without it.

### 1. Clone the repository

```bash
git clone https://github.com/TejashRajuKV/Echo-Mind.git
cd Echo-Mind
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your keys:

```bash
copy .env.example .env
```

Edit `.env`:

```env
# Required for Google Fact Check Tools API
GOOGLE_FACT_CHECK_API_KEY=your_key_here

# Required for live news retrieval
FREE_NEWS_API_KEY=your_key_here

# Required for Vertex AI / Gemini (leave blank to use deterministic fallback)
PROJECT_ID=your-gcp-project-id
LOCATION=asia-south1

# Security
SECRET_KEY=generate-a-random-string-here
ALLOWED_ORIGINS=http://localhost:8080
INTERNAL_API_KEY=your-admin-key

# Flask -- set to false in production
FLASK_DEBUG=false
```

> **Never commit `.env` to Git.** It is already listed in `.gitignore`.

See [API_SETUP_GUIDE.md](API_SETUP_GUIDE.md) for instructions on obtaining each key.

### 4. Start the backend server

```bash
python app.py
```

Server starts on **http://localhost:8080**.

### 5. Open the frontend

**Option A -- via Flask (recommended):**
Open `http://localhost:8080` in your browser.

**Option B -- direct file (also works):**
Open `index.html` directly from disk (`file:///...`). The frontend automatically detects `file://` protocol and routes all API calls to `localhost:8080`.

---

## Indian Language Support

Echo Mind detects the script of the input claim using Unicode block ranges and activates regional verification automatically:

| Language | Script | Regional Publishers |
|---|---|---|
| Kannada | U+0C80-U+0CFF | Prajavani, Vijayavani, Udayavani |
| Hindi | U+0900-U+097F | Dainik Jagran, Amar Ujala, Navbharat Times |
| Tamil | U+0B80-U+0BFF | Dinamalar, Dinakaran, The Hindu Tamil |
| Telugu | U+0C00-U+0C7F | Eenadu, Sakshi, Andhra Jyothi |
| Bengali | U+0980-U+09FF | Anandabazar Patrika, Prothom Alo |

The original vernacular wording is preserved in all analysis and reports to avoid meaning drift from translation.

---

## Security

| Area | Implementation |
|---|---|
| API Keys | Stored in `.env` only -- never in source code |
| CORS | Restricted to `ALLOWED_ORIGINS` env var (not `*`) |
| Rate Limiting | In-process per-IP limiter (configurable via `MAX_REQUESTS_PER_HOUR`); use a shared gateway/store for multi-worker production deployments |
| Session Isolation | Gamification state and history are scoped per session -- not shared globally |
| Fact-Check Isolation | User analysis logs stored in `analysis_logs` table, separate from the authoritative `fact_checks` table, to prevent circular self-reference contamination |
| Debug Mode | `FLASK_DEBUG=false` enforced in production |
| Input Validation | Claim length capped at `MAX_CLAIM_LENGTH` with type-checked JSON body parsing |

---

## Claim-monitor worker and notifications

The API stores monitor subscriptions but does not itself run a durable scheduler. Run the worker as a separate long-lived process or service:

```bash
python monitor_worker.py
```

Set `MONITOR_INTERVAL_MINUTES` to the desired check interval (minimum 5 minutes). For optional email alerts, configure SMTP host, port, username, password, and sender environment variables. If SMTP is not configured, in-app notifications remain available from `GET /monitor/notifications`; email alerts are not sent. On Cloud Run, deploy the worker separately from the request-serving service so scale-to-zero does not silently stop scheduled checks.

## Automated tests

The `backend-tests.yml` workflow runs the pytest regression suite and Python compilation checks on pushes to the hardening branch and on pull requests. Tests cover report escaping, conservative verdict reconciliation, request validation, and anonymous session isolation. CI results must pass before merging; a green test suite does not substitute for live API-key, SMTP, or deployment smoke tests.


## Context Memory and Incremental Verification

Echo Mind now includes a privacy-aware investigation memory layer in `context_memory.py` backed by `context_memory.db`.

- **Exact-claim cache:** reuses a source-backed analysis only while its cache entry is fresh. Claims with current/time-sensitive markers use a short 15-minute TTL; other claims use a 6-hour TTL. Expired entries are not returned as valid results and require revalidation.
- **Related-claim context:** uses normalized token overlap to suggest related investigations. Similarity is a navigation aid only; a prior verdict is never treated as evidence for a new or materially changed claim.
- **Investigation workspace:** saves session-scoped claims, verdict snapshots, event timelines, and links between related investigations.
- **Cross-language alias links:** users or a translation step can explicitly attach a translated wording to an investigation. Alias matches help locate prior work but are not proof that two claims have the same meaning.
- **Privacy controls:** investigation history is scoped to an anonymous session. Memory can be disabled, retention can be set from 1–365 days, and private history can be deleted. The shared exact-claim cache contains analysis output without session IDs or gamification state.
- **Forwarded-message analysis:** accepts pasted text or client-provided OCR text. The API does not claim to perform OCR itself; screenshot OCR must be performed by a client-side or separately configured OCR component.

### Context and workspace endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/context/prepare` | Find exact cache and related session investigations before analysis |
| `GET/POST` | `/investigations` | List investigations or create an unverified workspace item |
| `GET/DELETE` | `/investigations/<id>` | Read or delete an investigation owned by the current session |
| `POST` | `/investigations/<id>/events` | Add a note, evidence event, or open/resolved question |
| `POST` | `/investigations/<id>/aliases` | Attach a translated/paraphrased claim alias |
| `GET/POST` | `/memory/preferences` | Read or configure memory enabled state and retention |
| `DELETE` | `/memory/clear` | Delete private investigation history for the current session |
| `POST` | `/message/analyze` | Analyze a pasted or OCR-extracted forwarded message |
| `GET` | `/context/cache/expired` | Inspect expired cache entries for an administrator/scheduler; requires `X-API-Key` |

The shared cache is a latency optimization, not a guarantee of current truth. Deployments should monitor cache age, revalidate time-sensitive claims, and configure the existing evidence providers. Session IDs are hashed before persistence, but the service is not a substitute for authenticated user accounts when strict identity or multi-device ownership is required.

## Product Roadmap: Recommended Next Features

The following are **proposed next steps**, not claims that these features are already implemented. Priorities favour accuracy, measurable user value, and safe incremental delivery.

### P0 — Make incremental verification dependable

| Feature | What it should do | Acceptance criteria |
|---|---|---|
| **Automatic cache revalidation worker** | Process expired evidence-cache entries, re-fetch current sources, compare evidence and verdicts, and append a revalidation event instead of silently replacing history. | Worker is idempotent, records provider failures, and emits a before/after diff only when evidence or classification materially changes. |
| **Claim-family and entity matching** | Group wording variants around the same people, scheme, place, event, and factual assertion. Treat changed amounts, dates, eligibility, or locations as material differences. | Precision/recall are measured on a labelled set; uncertain matches are suggestions, not automatic verdict inheritance. |
| **Evidence provenance graph** | Link each subclaim to source passages, publication/update dates, publisher ownership or syndication groups, stance, and the reasoning step it supports. | Every decisive conclusion can be traced to source evidence; syndicated copies do not count as independent corroboration. |
| **Evidence freshness and change alerts** | Detect expired, corrected, removed, or materially updated sources and notify opted-in users when a saved investigation may need review. | Alerts cite the changed source and explain why the previous assessment may be stale; delivery failures are retried and observable. |
| **Evaluation and latency dashboard** | Benchmark verdict quality, citation coverage, source independence, abstention, cache hit rate, median/p95 latency, and verdict changes. | Metrics use labelled examples and report dataset size; speed improvements never hide stale evidence or reduce evidence requirements. |

### P1 — Improve the investigation experience

| Feature | What it should do | Guardrail |
|---|---|---|
| **Screenshot and forwarded-message checker** | Accept image uploads, run OCR, show extracted text for correction, identify separate claims and suspicious URLs, and verify each claim. | OCR uncertainty is visible; extracted text is not assumed accurate and image context is preserved. |
| **Automatic multilingual claim matching** | Match equivalent claims across English, Kannada, Hindi, Tamil, Telugu, Bengali, and other supported languages; search relevant regional sources. | Translation confidence and original wording are retained; aliases help retrieval but are never treated as proof of equivalence. |
| **Visual investigation workspace** | Present claim families, evidence cards, contradictions, timeline, open questions, and verdict history in one interface. | Private notes and history remain session/user-scoped; source citations are visible and exportable. |
| **Conflict explainer** | Explain whether sources disagree about the same fact or differ by date, definition, jurisdiction, or population. Highlight missing primary evidence. | The system may return “unresolved” instead of forcing consensus. |
| **Correction and review workflow** | Let users submit a correction with evidence, route it for review, and show whether it was accepted, rejected, or remains pending. | User votes and popularity never directly determine factual truth; review decisions are auditable. |

### P2 — Reach more users responsibly

- **Browser extension and share-sheet integration:** send a selected quote, URL, or forwarded message to Echo Mind and return a cited, compact result.
- **Claim-aware reading mode:** explain source quality, common reasoning traps, and how to verify the claim independently without lecturing the user.
- **Public, versioned fact-check pages:** show current assessment, dated evidence snapshots, correction history, and downloadable citations.
- **Community rumour trends:** aggregate privacy-preserving claim-family counts by time and region without exposing private conversation histories or identifying individual users.
- **Accessible voice and low-bandwidth mode:** support spoken claims, screen-reader-friendly evidence cards, and lightweight results for slower connections.

### Memory, privacy, and performance principles

1. **Separate three kinds of data:** private conversation/investigation history; shared, source-backed evidence cache; and public verification records. Never publish private notes by default.
2. **Use cache tiers:** exact, fresh matches may return quickly with their verification timestamp; related claims may reuse candidate sources but must re-check material differences; new or time-sensitive claims need fresh retrieval.
3. **Do not let user context become evidence:** prior messages help resolve references and intent, but claims from the user or old model outputs are not independent sources.
4. **Make retention and deletion meaningful:** document what is deleted, what remains in shared/public caches, and how retention works across backups and deployed instances.
5. **Measure accuracy before claiming improvement:** maintain a human-labelled, time-aware evaluation set with false-positive/false-negative analysis, language breakdowns, and abstention rates.
6. **Plan for production concurrency:** SQLite is suitable for a local/single-instance deployment; evaluate a shared transactional store and authenticated identities before relying on multi-instance writes or cross-device history.

### Suggested delivery order

1. Finish the expired-cache revalidation worker and verdict-diff timeline.
2. Build a labelled claim-family evaluation set, then improve entity/semantic matching against it.
3. Add the evidence provenance graph and expose its traceability in the investigation UI.
4. Connect screenshot OCR and multilingual matching only after the claim-extraction and evaluation paths are testable.
5. Use latency and quality metrics to prove the follow-up experience is faster without sacrificing freshness or citation quality.

## Deployment

### Google Cloud Run

```bash
deploy_to_cloud_run.bat
```

Or manually:

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/echo-mind
gcloud run deploy echo-mind --image gcr.io/YOUR_PROJECT_ID/echo-mind \
  --platform managed --region us-central1 --allow-unauthenticated
```

Set environment variables via Cloud Run's secret manager or environment variable configuration -- do **not** bundle `.env` into the container image.

---

## Technology Stack

### Frontend
- **HTML5 / CSS3 / JavaScript (ES6+)** -- no framework
- **Font Awesome 6** -- icons
- **Google Fonts -- Inter** -- typography

### Backend
- **Python 3.11** -- core language
- **Flask 3.x** -- API server
- **SQLite** -- five purpose-separated local databases
- **Google Vertex AI -- Gemini 2.5 Pro** -- AI reasoning (with deterministic fallback)
- **Google Fact Check Tools API** -- primary fact-check retrieval
- **FreeNewsAPI / NewsAPI** -- live news retrieval
- **Schema.org ClaimReview** -- structured data for search engines

---

## Recent Updates

- [x] **Evidence Intelligence Engine** -- retrieve-first, reason-second pipeline replacing black-box AI verdicts
- [x] **Multi-Source Verification & Conflict Detection** -- atomic sub-claim decomposition and consensus audit
- [x] **Echo-Chamber Deduplication** -- wire syndication clustering (PTI, AP, Reuters, ANI)
- [x] **Claim Evolution Tracker** -- mutation timelines and verdict drift detection
- [x] **Indian-Language Verification** -- Kannada, Hindi, Tamil, Telugu, Bengali with regional publisher registries
- [x] **Research Document Analysis** -- paragraph chunking and passage citation tracing
- [x] **Opt-In Claim Monitoring** -- SQLite-backed subscriber registry with update detection
- [x] **Shareable Evidence Reports** -- HTML + Google ClaimReview Schema.org JSON-LD
- [x] **Quality & Transparency Dashboard** -- real-time telemetry, latency, and human correction queue
- [x] **Security hardening** -- restrictive CORS, env-var keys, session isolation, separate analysis log table
- [x] **Windows CP1252 compatibility** -- all print statements use ASCII markers; no raw emoji in console output
- [x] **file:// protocol support** -- frontend auto-detects protocol and routes API calls to correct base URL

---

## Team -- Thunderwing Falcons

| Name | Role |
|---|---|
| **Tejash Raju K V** | Team Leader & Full-Stack Developer |
| **Amrutha V** | Frontend Developer & UX Designer |
| **Rakesh K** | Backend Developer & AI Specialist |

---

## Credits

- **Company**: Thunderwing Falcons -- *"Electrifying speed meets sharp precision"*
- **Prototype**: Echo Mind -- *"Suggesting intelligent responses and echoes of knowledge"*
- **Competition**: Google Hackathon AI Fact-Checker
- **Icons**: Font Awesome
- **Fonts**: Google Fonts (Inter)

## License

This project was created for educational and hackathon purposes.

---

**Thunderwing Falcons** -- Electrifying speed meets sharp precision  
**Echo Mind** -- Suggesting intelligent responses and echoes of knowledge


## Incremental verification sprint: implementation and operational notes

The following APIs are available in the current codebase. They are opt-in/explicit endpoints; scheduled execution still needs a scheduler or deployment cron.

| Endpoint | Purpose | Access |
|---|---|---|
| `POST /context/revalidate` | Re-run expired cache claims and record before/after verdict and score | `X-API-Key` required |
| `GET /context/revalidation-history?claim=...` | Inspect revalidation attempts and verdict changes | `X-API-Key` required |
| `POST /claim-family/compare` | Compare two claims, surface material numeric/negation changes, and advise re-verification | Rate-limited |
| `GET /claim-family/evaluation` | Run the curated JSONL claim-family benchmark and return precision/recall/F1 | `X-API-Key` required |
| `GET/POST /investigations/<id>/provenance` | Read or create a claim-to-source provenance graph for the current session's investigation | Session-scoped |
| `POST /message/ocr` | Extract text from an uploaded image with local Tesseract OCR | Optional OCR dependencies |
| `POST /message/language` | Best-effort language detection | Rate-limited |
| `POST /message/multilingual-match` | Find related session investigations, optionally using a translated query | Optional translation API key |
| `GET /public/fact-check?claim=...` | Generate a standalone shareable report from a fresh analysis | Public, rate-limited; not a permanent archival URL |
| `GET/POST /notifications` | Read or create session-scoped in-app notifications | Session-scoped |
| `POST /notifications/<id>/read` | Mark one caller-owned notification as read | Session-scoped |
| `GET /review/corrections` | List submitted human correction requests | `X-API-Key` required |
| `POST /review/corrections/<id>` | Mark a correction pending, accepted, rejected, or needing more evidence and record a moderator note | `X-API-Key` required |

### Running the incremental verification benchmark

Run the tests and the small labelled benchmark from the repository root:

```bash
python -m pytest -q
python -c "from incremental_verification import evaluate_claim_families; print(evaluate_claim_families())"
```

The initial `data/claim_family_eval.jsonl` file is a **small curated smoke dataset**, not a production accuracy claim. Use independently labelled, representative examples with hard negatives, regional languages, dates, amounts, negation, entity substitutions and temporal updates before selecting similarity thresholds. Similarity is a candidate-retrieval hint, never evidence of truth.

For follow-up latency experiments, prepare a separate JSONL file with independently human-labelled `claim` and `expected_verdict` fields, then run `python benchmark_followups.py your_labels.jsonl`. Add `--live` only when you intentionally want fresh provider-backed analyses (which may be slow and may incur API usage). The script reports context-lookup and live-analysis latency, and compares live verdicts with the supplied labels; it does not fabricate a quality score from unlabeled examples.

### Optional OCR and multilingual lookup

- OCR uses Pillow and `pytesseract`; install the Tesseract system executable separately and configure it in the runtime PATH. If unavailable, `POST /message/ocr` returns an explicit unavailable response rather than pretending OCR succeeded.
- Multilingual lookup uses language detection and session-private investigation history. If `GOOGLE_TRANSLATE_API_KEY` is configured, a translated query can be used to find candidates; translation is not evidence and all claims still require original-language source verification.
- OCR may misread amounts, dates, names and negations. The user must review extracted text before analysis.

### Revalidation and quality measurement

Call `POST /context/revalidate` periodically from a protected scheduler using the API key. Revalidation stores a run record, before/after verdict and score, source count, outcome and failure code. Failed runs leave the cache expired; they do not extend its freshness. Keep worker concurrency bounded and monitor failures. A route call does not itself create a recurring scheduler.

Measure follow-up investigation performance with a fixed labelled test set and record:
- end-to-end and retrieval median/p95 latency;
- cache hit rate and percentage of expired entries successfully revalidated;
- source citation coverage and independent-publisher count;
- verdict changes confirmed by human review;
- precision/recall/F1 of claim-family candidates, stratified by language and material changes;
- false positives, false negatives and abstention rate.

Compare repeated investigations against a fresh-analysis baseline. Do not report speed improvements unless measured on the same workload, and do not trade away source quality or verification accuracy for cache hits.
