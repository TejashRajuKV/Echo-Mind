"""Rule-based API routing for Echo Mind evidence retrieval.

The router favors direct fact-checks for claims, adds live reporting only when
freshness or weak initial evidence calls for it, and uses cached live context
for inherently changing subjects such as sports and weather.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict


TOPIC_TERMS = {
    "sports": ("cricket", "football", "soccer", "ipl", "fifa", "world cup", "match", "score", "captain", "tournament", "player"),
    "weather": ("weather", "rainfall", "temperature", "cyclone", "flood", "forecast", "monsoon"),
    "health": ("covid", "coronavirus", "vaccine", "medicine", "health", "disease", "virus", "treatment", "clinical", "hospital", "who "),
    "politics": ("election", "government", "minister", "parliament", "policy", "president", "prime minister", "vote"),
    "finance": ("stock", "share price", "inflation", "interest rate", "gdp", "market", "rupee", "economy", "budget"),
    "science": ("study", "research", "scientist", "experiment", "climate", "space", "technology", "scientific"),
}

FRESHNESS_TERMS = (
    "today", "currently", "right now", "latest", "this week", "this month", "breaking",
    "just announced", "recently", "as of", "current", "live",
)


def _has_key(*names: str) -> bool:
    return any(os.environ.get(name, "").strip() for name in names)


def _detect_language(claim: str) -> Dict[str, str]:
    try:
        from indian_language_engine import detect_indian_language
        info = detect_indian_language(claim)
        google_language_codes = {"kannada": "kn", "hindi": "hi", "tamil": "ta", "telugu": "te", "bengali": "bn"}
        detected_code = info.get("language_code", "en")
        return {
            "code": google_language_codes.get(detected_code, detected_code),
            "name": info.get("language_name", "English"),
        }
    except Exception:
        return {"code": "en", "name": "English"}


def build_api_decision(claim: str) -> Dict[str, Any]:
    """Choose source APIs from claim intent, language, freshness, and config."""
    normalized = " ".join(str(claim or "").lower().split())
    topic = "general"
    for candidate, terms in TOPIC_TERMS.items():
        if any(term in normalized for term in terms):
            topic = candidate
            break

    language = _detect_language(claim)
    time_sensitive = (
        topic in {"sports", "weather"}
        or any(term in normalized for term in FRESHNESS_TERMS)
        or bool(re.search(r"\b20\d{2}\b", normalized))
    )
    use_realtime_cache = topic in {"sports", "weather"} or "breaking news" in normalized or "live score" in normalized
    google_ready = _has_key("GOOGLE_FACT_CHECK_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
    news_key_ready = _has_key("FREE_NEWS_API_KEY", "FREENEWSAPI_KEY", "NEWSAPI_KEY", "NEWS_API_KEY")
    news_language_supported = language["code"] == "en"
    news_ready = news_key_ready and news_language_supported
    base_dir = Path(__file__).parent
    realtime_cache_ready = any((base_dir / filename).is_file() for filename in ("current_context.json", "api_current_context.json"))
    if _has_key("FREE_NEWS_API_KEY", "FREENEWSAPI_KEY"):
        news_provider = "FreeNewsAPI"
        news_fallback = "NewsAPI" if _has_key("NEWSAPI_KEY", "NEWS_API_KEY") else None
    else:
        news_provider = "NewsAPI"
        news_fallback = None

    return {
        "topic": topic,
        "language": language["name"],
        "language_code": language["code"],
        "time_sensitive": time_sensitive,
        "use_realtime_cache": use_realtime_cache,
        "routes": {
            "local_factchecks": {"configured": True, "used": True, "reason": "Always search the local verified archive first."},
            "google_fact_check": {
                "configured": google_ready,
                "used": google_ready,
                "provider": "Google Fact Check Tools API",
                "reason": "Search certified claim reviews for this factual claim." if google_ready else "Skipped: configure GOOGLE_FACT_CHECK_API_KEY (or a supported Google key) to enable certified claim reviews.",
            },
            "live_news": {
                "configured": news_ready,
                "used": False,
                "provider": news_provider,
                "fallback_provider": news_fallback,
                "reason": "Live reporting is reserved for time-sensitive claims or sparse direct evidence." if news_ready else ("Skipped: current news connectors are configured for English queries." if news_key_ready else "Skipped: no live-news API key is configured."),
            },
            "realtime_cache": {
                "configured": realtime_cache_ready,
                "used": False,
                "reason": (
                    "Use cached live context for sports, weather, and breaking news."
                    if use_realtime_cache and realtime_cache_ready
                    else "Skipped: no local live-context cache file is available."
                    if use_realtime_cache
                    else "Skipped: this claim does not need the sports/weather/breaking-news cache."
                ),
            },
        },
        "reasoning": "Gemini explains retrieved evidence when configured; otherwise the deterministic evidence-only fallback is used.",
    }


def finalize_api_decision(
    decision: Dict[str, Any], *, realtime_checked: bool, news_checked: bool,
    realtime_results: int, news_results: int, google_results: int,
    local_results: int, direct_source_count: int,
) -> Dict[str, Any]:
    """Attach actual retrieval outcomes to the initial routing plan."""
    result = {**decision, "routes": {name: dict(route) for name, route in decision["routes"].items()}}
    result["routes"]["google_fact_check"]["results_found"] = google_results
    result["routes"]["local_factchecks"]["results_found"] = local_results
    realtime = result["routes"]["realtime_cache"]
    realtime["used"] = bool(realtime_checked)
    if realtime_checked and realtime_results:
        realtime["reason"] = "Matching cached real-time context was added to the evidence set."
    elif realtime_checked:
        realtime["reason"] = "Checked the cache, but it had no matching current context."

    news = result["routes"]["live_news"]
    news["used"] = bool(news_checked)
    if news_checked and news_results:
        news["reason"] = "Added live reporting because freshness mattered or direct evidence was sparse."
    elif news_checked:
        news["reason"] = "Queried live reporting, but no matching articles were returned."
    elif news["configured"]:
        news["reason"] = "Skipped: direct fact-check and archive results were sufficient for this claim."

    result["direct_source_count"] = direct_source_count
    realtime["results_found"] = realtime_results
    news["results_found"] = news_results
    return result
