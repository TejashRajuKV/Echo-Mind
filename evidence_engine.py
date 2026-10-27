"""
evidence_engine.py — Evidence Intelligence Engine for Echo Mind
===============================================================
A multi-tier evidence retrieval, ranking, and deduplication engine that
gathers primary and secondary sources before AI reasoning.

Key Capabilities:
1. FreeNewsAPI & NewsAPI live news connectors
2. Verified Local Fact-Check Database connector
3. Real-time auto-updater context integration
4. Domain Authority scoring (Government/Academic/Wires/Commercial)
5. Echo-chamber & Wire Syndication detection (deduplication of mirrored articles)
6. Source Stance Tagging (Supports / Refutes / Neutral Context)
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Domain Authority Knowledge Base (Curated Tiered Weightings 0-100)
# ---------------------------------------------------------------------------
AUTHORITY_TIERS = {
    # Tier 1A: Official Government, Intergovernmental & Public Health (95-100)
    "gov": 98,
    "gov.in": 98,
    "pib.gov.in": 99,
    "who.int": 98,
    "un.org": 98,
    "cdc.gov": 98,
    "nih.gov": 98,
    "isro.gov.in": 98,
    "nasa.gov": 98,
    "eci.gov.in": 98,
    "rbi.org.in": 98,

    # Tier 1B: Peer-Reviewed Scientific & Academic Journals (92-97)
    "nature.com": 96,
    "science.org": 96,
    "thelancet.com": 96,
    "nejm.org": 96,
    "cell.com": 95,
    "pubmed.ncbi.nlm.nih.gov": 95,
    "arxiv.org": 90,
    "edu": 90,
    "ac.in": 90,

    # Tier 2A: Certified Fact-Checking Organizations & Primary Wires (88-95)
    "snopes.com": 94,
    "politifact.com": 94,
    "factcheck.org": 94,
    "altnews.in": 93,
    "boomlive.in": 93,
    "vishvasnews.com": 91,
    "reuters.com": 93,
    "apnews.com": 93,
    "afp.com": 92,
    "fullfact.org": 92,

    # Tier 2B: Global & National High-Credibility Broadcasters / Press (80-89)
    "bbc.com": 89,
    "bbc.co.uk": 89,
    "thehindu.com": 87,
    "indianexpress.com": 86,
    "timesofindia.indiatimes.com": 82,
    "hindustantimes.com": 83,
    "ndtv.com": 84,
    "nytimes.com": 88,
    "washingtonpost.com": 87,
    "theguardian.com": 87,
    "wsj.com": 87,
    "bloomberg.com": 87,
    "aljazeera.com": 83,
    "news18.com": 79,
    "livemint.com": 82,
    "business-standard.com": 83,
    "deccanherald.com": 82,
}

# Known syndication wires & agencies
WIRE_SERVICES = ["pti", "press trust of india", "ani", "asian news international", "reuters", "associated press", "ap wire", "afp", "ians"]


def extract_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def get_domain_authority(url: str, publisher_name: str = "") -> Dict[str, Any]:
    """
    Compute domain authority score (0-100) and tier categorization.
    """
    domain = extract_domain(url)
    score = 50  # Default unverified baseline
    tier = "General Source"

    # Match domain or sub-domain
    matched = False
    for pattern, auth_score in AUTHORITY_TIERS.items():
        if domain == pattern or domain.endswith("." + pattern):
            score = auth_score
            matched = True
            break

    if not matched and publisher_name:
        pub_lower = publisher_name.lower()
        for pattern, auth_score in AUTHORITY_TIERS.items():
            if pattern in pub_lower:
                score = auth_score
                matched = True
                break

    # Determine authority tier
    if score >= 95:
        tier = "Tier 1: Official & Primary Institution"
    elif score >= 88:
        tier = "Tier 2: Certified Fact-Checker / Wire"
    elif score >= 80:
        tier = "Tier 3: Reputable News Publisher"
    elif score >= 65:
        tier = "Tier 4: Standard Media Outlet"
    else:
        tier = "Tier 5: Unverified / Community Source"

    return {
        "domain": domain,
        "score": score,
        "tier": tier,
        "is_high_authority": score >= 80,
    }


def detect_syndication(title: str, text: str, publisher: str) -> Dict[str, Any]:
    """
    Identify whether an article is syndicated wire copy or original reporting.
    """
    text_sample = f"{title} {text} {publisher}".lower()
    syndicated = False
    wire_detected = ""

    for wire in WIRE_SERVICES:
        if wire in text_sample or f"({wire})" in text_sample or f"source: {wire}" in text_sample:
            syndicated = True
            wire_detected = wire.upper()
            break

    # Compute a signature hash based on normalized title to cluster reposts
    normalized = re.sub(r'[^a-z0-9 ]', '', title.lower()).strip()
    words = [w for w in normalized.split() if len(w) > 3][:6]
    cluster_id = hashlib.md5(" ".join(words).encode()).hexdigest()[:10] if words else "standalone"

    return {
        "is_syndicated": syndicated,
        "wire_agency": wire_detected,
        "cluster_id": cluster_id,
    }


def detect_evidence_stance(claim: str, title: str, text: str, rating: str = "") -> str:
    """
    Determine whether evidence supports, refutes, or is neutral towards a claim.
    Returns: 'supports' | 'refutes' | 'neutral'
    """
    # 1. Prioritize explicit fact-check rating if provided
    if rating:
        r_lower = rating.lower().strip()
        if re.search(r'\b(false|fake|hoax|misleading|pants on fire|incorrect|debunked|untrue|myth|fabricated|scam)\b', r_lower):
            return "refutes"
        if re.search(r'\b(true|correct|accurate|verified|confirmed|factual|authentic)\b', r_lower):
            return "supports"

    combined = f"{title} {text}".lower()

    # 2. Check for explicit refutation keywords
    if re.search(r'\b(debunked|false claim|misinformation|hoax|conspiracy theory|fact-checked: false|unfounded|fabricated)\b', combined):
        return "refutes"

    # 3. Check for explicit confirmation
    if re.search(r'\b(confirmed by|officially announced|study proves|verified report|scientific consensus confirms)\b', combined):
        return "supports"

    return "neutral"


# ---------------------------------------------------------------------------
# Source Connector 1: FreeNewsAPI & NewsAPI Connector
# ---------------------------------------------------------------------------
def query_live_news_sources(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Query FreeNewsAPI.io or NewsAPI.org for primary news reporting.
    """
    results = []
    free_news_key = os.environ.get("FREE_NEWS_API_KEY") or os.environ.get("FREENEWSAPI_KEY")
    news_api_key = os.environ.get("NEWSAPI_KEY") or os.environ.get("NEWS_API_KEY")

    clean_query = " ".join([w for w in query.split() if len(w) > 2][:6])

    # 1. Try FreeNewsAPI
    if free_news_key:
        try:
            url = f"https://www.freenewsapi.io/api/v1/search?query={requests.utils.quote(clean_query)}&token={free_news_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and "json" in resp.headers.get("content-type", "").lower():
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                articles = data.get("articles", []) or data.get("data", [])
                for art in articles[:max_results]:
                    title = art.get("title", "")
                    desc = art.get("description", "") or art.get("snippet", "")
                    url_art = art.get("url", "") or art.get("link", "")
                    source_name = art.get("source", {}).get("name", "") if isinstance(art.get("source"), dict) else str(art.get("source", "News"))
                    pub_date = art.get("publishedAt", "") or art.get("date", "")

                    if not title:
                        continue

                    auth = get_domain_authority(url_art, source_name)
                    synd = detect_syndication(title, desc, source_name)
                    stance = detect_evidence_stance(query, title, desc)

                    results.append({
                        "source_type": "live_news",
                        "title": title,
                        "publisher": source_name or auth["domain"] or "News Source",
                        "url": url_art,
                        "date": pub_date[:10] if pub_date else "",
                        "textual_rating": "",
                        "stance": stance,
                        "excerpt": desc[:250] if desc else title,
                        "authority_score": auth["score"],
                        "authority_tier": auth["tier"],
                        "domain": auth["domain"],
                        "is_syndicated": synd["is_syndicated"],
                        "cluster_id": synd["cluster_id"],
                        "wire_agency": synd["wire_agency"],
                    })
        except Exception as e:
            print(f"[WARN] FreeNewsAPI query error: {e}")

    # A broad name match is not enough for sensitive claims such as death
    # rumors. Let the backup provider run when all FreeNews results are noise.
    if results:
        try:
            from api_decision_engine import is_relevant_news_article
            results = [item for item in results if is_relevant_news_article(query, item)]
        except Exception as exc:
            print(f"[WARN] Could not filter FreeNewsAPI results: {type(exc).__name__}")

    # 2. Fallback / Complement with NewsAPI if available
    if not results and news_api_key:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": clean_query,
                "apiKey": news_api_key,
                "pageSize": max_results,
                "sortBy": "relevancy",
                "language": "en",
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200 and "json" in resp.headers.get("content-type", "").lower():
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                for art in data.get("articles", [])[:max_results]:
                    title = art.get("title", "")
                    desc = art.get("description", "") or ""
                    url_art = art.get("url", "")
                    source_name = art.get("source", {}).get("name", "")
                    pub_date = art.get("publishedAt", "")

                    auth = get_domain_authority(url_art, source_name)
                    synd = detect_syndication(title, desc, source_name)
                    stance = detect_evidence_stance(query, title, desc)

                    results.append({
                        "source_type": "live_news",
                        "title": title,
                        "publisher": source_name or auth["domain"],
                        "url": url_art,
                        "date": pub_date[:10] if pub_date else "",
                        "textual_rating": "",
                        "stance": stance,
                        "excerpt": desc[:250] if desc else title,
                        "authority_score": auth["score"],
                        "authority_tier": auth["tier"],
                        "domain": auth["domain"],
                        "is_syndicated": synd["is_syndicated"],
                        "cluster_id": synd["cluster_id"],
                        "wire_agency": synd["wire_agency"],
                    })
        except Exception as e:
            print(f"[WARN] NewsAPI query error: {e}")

    return results


# ---------------------------------------------------------------------------
# Source Connector 2: Local SQLite Fact-Check Database Connector
# ---------------------------------------------------------------------------
def query_local_factcheck_db(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search curated local fact checks in factchecks.db.
    """
    results = []
    try:
        from database_helper import get_database_connection
        conn = get_database_connection()
        cursor = conn.cursor()

        words = [w for w in query.lower().split() if len(w) > 2]
        query_sql = """
            SELECT claim, verdict, source, url, explanation, created_at
            FROM fact_checks
            WHERE LOWER(claim) LIKE ?
        """
        params = [f"%{query.lower()}%"]

        cursor.execute(query_sql, params)
        rows = cursor.fetchall()

        if not rows and words:
            sub_clauses = ["LOWER(claim) LIKE ?"] * min(len(words), 3)
            sql = f"SELECT claim, verdict, source, url, explanation, created_at FROM fact_checks WHERE {' OR '.join(sub_clauses)} LIMIT ?"
            params = [f"%{w}%" for w in words[:3]] + [max_results]
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        conn.close()

        for row in rows[:max_results]:
            row_dict = dict(row)
            source_name = row_dict.get("source", "Verified Database")
            url = row_dict.get("url", "")
            verdict = row_dict.get("verdict", "")
            explanation = row_dict.get("explanation", "")
            title = f"{row_dict.get('claim', '')} — {verdict}"

            auth = get_domain_authority(url, source_name)
            auth["score"] = max(auth["score"], 90)
            synd = detect_syndication(title, explanation, source_name)
            stance = detect_evidence_stance(query, title, explanation, verdict)

            results.append({
                "source_type": "database_fact_check",
                "title": title,
                "publisher": source_name,
                "url": url,
                "date": str(row_dict.get("created_at", ""))[:10],
                "textual_rating": verdict,
                "stance": stance,
                "excerpt": explanation[:250] if explanation else f"Claim verdict: {verdict}",
                "authority_score": auth["score"],
                "authority_tier": auth["tier"],
                "domain": auth["domain"] or "echomind.local",
                "is_syndicated": synd["is_syndicated"],
                "cluster_id": synd["cluster_id"],
                "wire_agency": synd["wire_agency"],
            })
    except Exception as e:
        print(f"[WARN] Local database query error: {e}")

    return results


# ---------------------------------------------------------------------------
# Source Connector 4: Real-Time Auto-Updater Context
# ---------------------------------------------------------------------------
def query_realtime_updater_context(query: str) -> List[Dict[str, Any]]:
    """
    Search auto-updater cache (api_current_context.json / current_context.json)
    for sports, weather, and breaking events.
    """
    results = []
    try:
        from analysis_engine import load_current_context
        context = load_current_context()
        if not context:
            return []

        q_lower = query.lower()
        for match in context.get("sports_matches", []):
            teams = match.get("teams", "")
            summary = match.get("summary", "")
            if any(term in q_lower for term in teams.lower().split()):
                results.append({
                    "source_type": "real_time_sports",
                    "title": f"Live Cricket Match: {teams}",
                    "publisher": "Official Live Sports Feed",
                    "url": "https://cricapi.com",
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "textual_rating": "Live Score",
                    "stance": "supports",
                    "excerpt": f"{teams}: {summary}. Current status: {match.get('status', 'In Progress')}",
                    "authority_score": 95,
                    "authority_tier": "Tier 1: Official Primary Feed",
                    "domain": "cricapi.com",
                    "is_syndicated": False,
                    "cluster_id": "live-sports",
                    "wire_agency": "",
                })

        for item in context.get("breaking_news", []):
            headline = item.get("title", "")
            desc = item.get("description", "")
            if any(w in headline.lower() for w in q_lower.split() if len(w) > 3):
                auth = get_domain_authority(item.get("url", ""), item.get("source", ""))
                synd = detect_syndication(headline, desc, item.get("source", ""))
                stance = detect_evidence_stance(query, headline, desc)

                results.append({
                    "source_type": "breaking_news",
                    "title": headline,
                    "publisher": item.get("source", "Breaking News"),
                    "url": item.get("url", ""),
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "textual_rating": "",
                    "stance": stance,
                    "excerpt": desc[:250],
                    "authority_score": auth["score"],
                    "authority_tier": auth["tier"],
                    "domain": auth["domain"],
                    "is_syndicated": synd["is_syndicated"],
                    "cluster_id": synd["cluster_id"],
                    "wire_agency": synd["wire_agency"],
                })
    except Exception as e:
        print(f"[WARN] Real-time context query error: {e}")

    return results


# ---------------------------------------------------------------------------
# Master Evidence Retrieval & Deduplication Pipeline
# ---------------------------------------------------------------------------
def gather_evidence_pipeline(claim: str, max_total: int = 10) -> Dict[str, Any]:
    """
    Executes an adaptive evidence pipeline:
    1. Selects relevant connectors for the claim and configured API keys
    2. Uses live news when the claim is time-sensitive or initial evidence is sparse
    3. Deduplicates wire copies & groups echo-clusters
    4. Ranks by Domain Authority + Stance Relevance
    5. Computes source distribution statistics
    """
    from api_decision_engine import build_api_decision, finalize_api_decision, is_relevant_news_article
    from verification_engine import publisher_identity

    raw_sources: List[Dict[str, Any]] = []
    decision = build_api_decision(claim)

    # The local archive is always queried as it has no external API cost.
    db_sources = query_local_factcheck_db(claim, max_results=4)
    raw_sources.extend(db_sources)

    direct_sources = db_sources
    direct_stances = {source.get("stance") for source in direct_sources}
    direct_publishers = {publisher_identity(source) for source in direct_sources}
    # Repeated URLs or multiple records from one outlet are not independent
    # coverage and should not suppress the live-news follow-up route.
    direct_source_count = len(direct_publishers)
    evidence_is_sparse = direct_source_count < 2
    direct_evidence_conflicts = "supports" in direct_stances and "refutes" in direct_stances
    needs_live_news = decision["time_sensitive"] or evidence_is_sparse or direct_evidence_conflicts

    # Cached live context is only relevant to rapidly changing claims.
    rt_route = decision["routes"]["realtime_cache"]
    realtime_checked = rt_route["configured"] and decision["use_realtime_cache"]
    rt_sources = query_realtime_updater_context(claim) if (
        realtime_checked
    ) else []
    raw_sources.extend(rt_sources)

    # News is a follow-up connector, not a default call for every claim.
    news_route = decision["routes"]["live_news"]
    news_checked = news_route["configured"] and needs_live_news
    news_query = decision.get("live_news_query") or claim
    news_sources = query_live_news_sources(news_query, max_results=8) if news_checked else []
    if news_sources:
        news_sources = [source for source in news_sources if is_relevant_news_article(claim, source)][:4]
    raw_sources.extend(news_sources)
    decision = finalize_api_decision(
        decision,
        realtime_checked=realtime_checked,
        news_checked=news_checked,
        realtime_results=len(rt_sources),
        news_results=len(news_sources),
        local_results=len(db_sources),
        direct_source_count=direct_source_count,
    )

    # --- Deduplication and Cluster Analysis ---
    seen_urls = set()
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    deduped_sources: List[Dict[str, Any]] = []

    for src in raw_sources:
        url = src.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        cid = src.get("cluster_id", "standalone")
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(src)

    for cid, items in clusters.items():
        sorted_items = sorted(items, key=lambda x: x.get("authority_score", 0), reverse=True)
        rep = sorted_items[0]
        echo_count = len(sorted_items) - 1
        rep["echo_count"] = echo_count
        rep["is_echo_chamber"] = echo_count >= 1
        deduped_sources.append(rep)

    deduped_sources.sort(key=lambda x: x.get("authority_score", 0), reverse=True)
    top_sources = deduped_sources[:max_total]

    supports_count = sum(1 for s in top_sources if s["stance"] == "supports")
    refutes_count = sum(1 for s in top_sources if s["stance"] == "refutes")
    neutral_count = sum(1 for s in top_sources if s["stance"] == "neutral")
    avg_authority = (
        round(sum(s["authority_score"] for s in top_sources) / len(top_sources), 1)
        if top_sources else 50.0
    )

    return {
        "claim": claim,
        "total_sources_found": len(raw_sources),
        "unique_sources_retained": len(top_sources),
        "sources": top_sources,
        "stance_summary": {
            "supports": supports_count,
            "refutes": refutes_count,
            "neutral": neutral_count,
        },
        "average_authority_score": avg_authority,
        "has_primary_evidence": any(s["authority_score"] >= 90 for s in top_sources),
        "api_decision": decision,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    print("Testing Evidence Intelligence Engine...")
    test_claim = "WHO declares global health emergency"
    res = gather_evidence_pipeline(test_claim)
    print(f"Found {res['total_sources_found']} sources, retained {res['unique_sources_retained']}.")
    print("Top Source:", json.dumps(res["sources"][:1], indent=2))
