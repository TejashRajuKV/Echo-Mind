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

Echo Mind is a production-grade AI fact-checking platform that **retrieves and audits evidence first, then reasons over it** — rather than relying on the model's own knowledge alone. Every verdict is backed by an auditable evidence trail with source titles, publisher names, publication dates, and direct URLs.

The system runs on Google Vertex AI (Gemini 2.5 Pro) with a deterministic fallback pipeline when Vertex AI is unavailable, so it works fully offline or in local development.

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
| **Opt-In Claim Monitoring** | Subscribe to follow any claim. Alerts are stored in `claim_monitors.db` and triggered when significant new evidence or a verdict correction emerges. |
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
| Rate Limiting | Per-session in-process limiter (configurable via `MAX_REQUESTS_PER_HOUR`) |
| Session Isolation | Gamification state and history are scoped per session -- not shared globally |
| Fact-Check Isolation | User analysis logs stored in `analysis_logs` table, separate from the authoritative `fact_checks` table, to prevent circular self-reference contamination |
| Debug Mode | `FLASK_DEBUG=false` enforced in production |
| Input Validation | Claim length capped at `MAX_CLAIM_LENGTH` with type-checked JSON body parsing |

---

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
