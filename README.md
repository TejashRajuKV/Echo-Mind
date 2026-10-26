# Echo Mind

Echo Mind is an evidence-first fact-checking website. It retrieves source material first, audits source stance and independence, then uses Gemini to explain what that evidence does and does not establish.

A verdict is only as dependable as the retrieved sources. Publisher authority, stance, freshness, and syndication are automated signals and may be imperfect. Treat results as research guidance, not a substitute for checking primary records.

## Live deployment

- Frontend: GitHub Pages at https://tejashrajukv.github.io/Echo-Mind/
- Backend API: Render at https://echo-mind-5act.onrender.com/
- The frontend calls the Render service configured in script.js as ECHO_MIND_API_BASE.
- The Flask backend also serves the frontend locally from the same origin.

The GitHub Pages workflow deploys the repository root on pushes to main. Render must be configured to deploy the Python service from main. A healthy /health response confirms the service is reachable; it does not confirm every provider key or feature is configured.

## How a claim check works

1. The API decision engine chooses which retrieval providers to use based on claim topic, language, freshness, available keys, and evidence already found.
2. The backend searches the local fact-check archive and, when configured, Google Fact Check Tools. It adds cached real-time context for relevant fast-changing topics.
3. When live-news credentials are configured, news search is used for time-sensitive claims or when the first evidence pass is sparse or conflicting.
4. The verification engine labels source direction, groups likely syndicated copies, decomposes compound claims, and calculates an evidence score.
5. Gemini receives the retrieved evidence and audit to write an explanation. It does not act as the news provider. GEMINI_API_KEY selects the Gemini Developer API; without it, the backend can use configured Vertex AI credentials. If neither client is available, it uses a deterministic evidence-only explanation.
6. Verdict reconciliation can downgrade a model label. A decisive result requires independent directional evidence; neutral coverage does not count as a vote. Conflicting or insufficient evidence is reported as Suspicious / unverified.

Some connectors are skipped when their API keys are absent. A successful page load or healthy backend does not mean every external provider is available.

## Features

| Feature | What is implemented | Dependencies and limits |
|---|---|---|
| Claim fact-checking | Evidence retrieval, source cards, stance/conflict audit, claim decomposition, conservative verdict reconciliation, credibility breakdown | Quality depends on available sources and their metadata |
| API decision engine | Shows selected source routes and why a route was used or skipped | Live providers require their keys; local archive is always queried |
| Gemini explanation | Explains retrieved evidence and supports grounded follow-up questions | Uses GEMINI_API_KEY or configured Vertex AI credentials; otherwise deterministic fallback |
| Evidence trail | Search, stance filter, authority sorting, citation export | Authority and stance are automated estimates |
| Claim library and history | Recent and saved checks with points/badges | Anonymous browser-generated session ID; no login or cross-device sync |
| Investigation workspace | Session-scoped investigation files, event notes, provenance graph, and source lists | SQLite-backed; hosted persistence depends on the service's disk configuration |
| Claim comparison and evolution | Compares wording and material changes; tracks related claim history | Similarity is a navigation hint, never evidence |
| Indian-language support | Detects Kannada, Hindi, Tamil, Telugu, and Bengali scripts; optional translated candidate lookup | Translation is optional and never counts as evidence |
| Document analysis | Chunks pasted documents and cites extracted passages | Output still needs human review |
| Image OCR | Optional text extraction from uploaded images | Requires Pillow, pytesseract, and the Tesseract executable; OCR can misread text |
| Monitoring and notifications | Opt-in subscriptions, update checks, and in-app notifications | Scheduled checks require monitor_worker.py running as a separate process; email also needs SMTP |
| Reports | Shareable HTML report and ClaimReview JSON-LD | Public report generation is rate-limited and re-runs a check |
| Transparency and corrections | Quality metrics, correction submissions, and protected review queue | Admin routes require ECHO_MIND_API_KEY |
| Cache revalidation | Protected endpoint and worker to re-check expired source-backed cache entries | Needs a scheduled/supervised worker; SQLite should not be shared across replicas |

### Session and data storage

There is no account login. The browser generates an anonymous session ID and sends it to the backend to scope history, saved investigations, preferences, and notifications. Clearing browser storage creates a new session identity. This is not authenticated identity and should not be used for strict ownership or multi-device access.

The application uses SQLite files on the backend filesystem. On hosted services, SQLite data can be lost when an instance is replaced unless persistent storage is configured. Use a persistent disk or a managed database before relying on long-term user history.

## Local development

Requirements: Python 3.11+ and pip.

1. Create a virtual environment and install dependencies: python -m venv .venv, then activate it and run python -m pip install -r requirements.txt.
2. Copy .env.example to .env and add the keys you want to use. Never publish .env.
3. Start the server with python app.py.
4. Open http://localhost:8080. Flask serves both the frontend and API on this origin.

On Windows PowerShell, activate the environment with .venv\Scripts\Activate.ps1. If PowerShell blocks activation, use the Python executable inside .venv directly.

## Configuration

| Variable | Purpose |
|---|---|
| GEMINI_API_KEY | Gemini Developer API key; preferred for grounded explanations and follow-up answers |
| GEMINI_MODEL | Gemini model name; defaults to gemini-3.5-flash |
| PROJECT_ID and LOCATION | Vertex AI project and region, used when no Gemini Developer API key is configured |
| GOOGLE_FACT_CHECK_API_KEY | Enables Google Fact Check Tools retrieval |
| FREE_NEWS_API_KEY or FREENEWSAPI_KEY | Enables FreeNewsAPI retrieval |
| NEWSAPI_KEY or NEWS_API_KEY | NewsAPI fallback when FreeNewsAPI is unavailable or not configured |
| ECHO_MIND_API_KEY | Protects admin/maintenance endpoints such as statistics and correction review |
| ALLOWED_ORIGINS | Comma-separated browser origins allowed by CORS; for Pages include https://tejashrajukv.github.io (no path) |
| PORT | HTTP port; Render supplies this automatically |
| FLASK_DEBUG | Keep false in hosted environments |
| MAX_REQUESTS_PER_HOUR | Per-process rate limit |
| MAX_CLAIM_LENGTH | Maximum claim text length |

The Gemini key stays on the backend and must never be placed in browser JavaScript or a public GitHub Pages variable. API providers have their own quotas and terms. ECHO_MIND_API_KEY protects administrative requests and remains a legacy Gemini-key fallback for older deployments; set GEMINI_API_KEY separately so the two secrets are not confused.

## Deploying

### GitHub Pages frontend

The .github/workflows/static.yml workflow publishes the repository root from main. The frontend API base currently points to the Render URL above. If the backend URL changes, update ECHO_MIND_API_BASE in script.js, then push the frontend change.

### Render backend

Configure a Render Web Service for this repository and main:

- Build command: pip install -r requirements.txt
- Start command: python app.py
- Add required keys and ALLOWED_ORIGINS in Render's environment settings. Do not upload .env.
- Use a persistent disk for SQLite data if history must survive instance replacement.
- Run monitoring or cache revalidation workers separately from the web process.

The backend's ALLOWED_ORIGINS must include the GitHub Pages origin exactly. CORS is browser access control, not API authentication.

## API routes

Session-scoped routes use the X-Session-ID header. Protected maintenance and review routes use X-API-Key.

| Area | Routes |
|---|---|
| Core checking | POST /analyze, POST /followup, GET /history, GET /evolution |
| Investigations | GET/POST /investigations, GET/DELETE /investigations/<id>, POST /investigations/<id>/events, POST /investigations/<id>/aliases, GET/POST /investigations/<id>/provenance |
| Documents and messages | POST /document/analyze, POST /message/analyze, POST /message/ocr, POST /message/language, POST /message/multilingual-match |
| Monitoring and notifications | POST /monitor/subscribe, GET /monitor/list, GET /monitor/notifications, GET/POST /notifications, POST /notifications/<id>/read |
| Reports and quality | GET /report, GET /public/fact-check, GET /transparency, POST /correction |
| Preferences and cache | GET/POST /memory/preferences, DELETE /memory/clear, POST /context/prepare, GET /context/cache/expired, POST /context/revalidate, GET /context/revalidation-history |
| Claim families | POST /claim-family/compare, GET /claim-family/evaluation |
| Admin and service | GET /health, GET /stats, GET /review/corrections, POST /review/corrections/<id> |

See API_SETUP_GUIDE.md, AUTO_UPDATE_GUIDE.md, and RAG_SYSTEM_GUIDE.md for provider setup and optional services.

## Checks

Install optional test tools with python -m pip install pytest schedule and npm install --no-save --no-package-lock @playwright/test, then install the browser with npx playwright install chromium.

- Backend regression suite: python -m pytest -q
- Standard-library regression suite: python -m unittest discover -s tests -v
- Frontend browser checks: npx playwright test
- JavaScript syntax: node --check script.js
- Python compilation: python -m compileall -q app.py analysis_engine.py evidence_engine.py verification_engine.py verdict_policy.py

The browser suite uses deterministic mocked API responses. It does not verify live Gemini, news-provider credentials, Render persistence, or deployment configuration. API-backed behavior should be checked separately with the provider keys and deployed service.

## Repository layout

- index.html, styles.css, script.js: static frontend
- app.py: Flask app, API routes, CORS, session and request handling
- analysis_engine.py: orchestration, Gemini explanation, and final verdict
- evidence_engine.py, api_decision_engine.py: retrieval providers and routing
- verification_engine.py, verdict_policy.py: source stance, independence, consensus, and scores
- context_memory.py, claim_evolution.py, incremental_verification.py: investigations, cache, and claim history
- document_analysis.py, ocr_support.py, indian_language_engine.py: documents, OCR, and language support
- claim_monitor.py, monitor_worker.py, notification_store.py: subscriptions and notifications
- shareable_report.py, transparency_dashboard.py: reports, metrics, and corrections
- tests/: Python regression and Playwright browser tests
