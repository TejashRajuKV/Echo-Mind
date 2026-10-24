"""
indian_language_engine.py — Indian-Language Verification Engine
==============================================================
Provides native support for Kannada, Hindi, Tamil, Telugu, Bengali,
and other Indian languages with vernacular preservation and regional-source discovery.
"""

import re
from typing import Dict, Any, List, Optional

# Supported Indian Language Script Signatures
SCRIPT_RANGES = {
    "kannada": {
        "name": "Kannada",
        "native": "ಕನ್ನಡ",
        "pattern": r'[\u0C80-\u0CFF]',
        "trusted_sources": [
            {"name": "Prajavani", "domain": "prajavani.net", "authority": 88, "tier": "Regional Premier Press"},
            {"name": "Vijayavani", "domain": "vijayavani.net", "authority": 84, "tier": "Regional Daily"},
            {"name": "Kannada Prabha", "domain": "kannadaprabha.com", "authority": 85, "tier": "Regional Daily"},
            {"name": "Vartha Bharati", "domain": "varthabharati.in", "authority": 82, "tier": "Regional News"},
            {"name": "Karnataka DIPR Official", "domain": "dipr.karnataka.gov.in", "authority": 98, "tier": "Tier-1 Official Government"},
        ]
    },
    "hindi": {
        "name": "Hindi",
        "native": "हिन्दी",
        "pattern": r'[\u0900-\u097F]',
        "trusted_sources": [
            {"name": "Dainik Jagran", "domain": "jagran.com", "authority": 85, "tier": "National Daily"},
            {"name": "Amar Ujala", "domain": "amarujala.com", "authority": 84, "tier": "National Daily"},
            {"name": "Dainik Bhaskar", "domain": "bhaskar.com", "authority": 85, "tier": "National Daily"},
            {"name": "Navbharat Times", "domain": "navbharattimes.indiatimes.com", "authority": 86, "tier": "National Press"},
            {"name": "BBC Hindi", "domain": "bbc.com/hindi", "authority": 92, "tier": "Tier-2 Certified Broadcaster"},
            {"name": "Vishvas News (Hindi Fact-Check)", "domain": "vishvasnews.com", "authority": 93, "tier": "Tier-2 Certified Fact-Checker"},
            {"name": "PIB Fact Check (GoI)", "domain": "pib.gov.in", "authority": 99, "tier": "Tier-1 Official Government"},
        ]
    },
    "tamil": {
        "name": "Tamil",
        "native": "தமிழ்",
        "pattern": r'[\u0B80-\u0BFF]',
        "trusted_sources": [
            {"name": "Dinamalar", "domain": "dinamalar.com", "authority": 85, "tier": "Regional Daily"},
            {"name": "Dinakaran", "domain": "dinakaran.com", "authority": 83, "tier": "Regional Daily"},
            {"name": "BBC Tamil", "domain": "bbc.com/tamil", "authority": 92, "tier": "Tier-2 Certified Broadcaster"},
            {"name": "YouTurn (Tamil Fact-Check)", "domain": "youturn.in", "authority": 90, "tier": "Certified Fact-Checker"},
        ]
    },
    "telugu": {
        "name": "Telugu",
        "native": "తెలుగు",
        "pattern": r'[\u0C00-\u0C7F]',
        "trusted_sources": [
            {"name": "Eenadu", "domain": "eenadu.net", "authority": 88, "tier": "Regional Premier Press"},
            {"name": "Sakshi", "domain": "sakshi.com", "authority": 83, "tier": "Regional Daily"},
            {"name": "Andhra Jyothi", "domain": "andhrajyothy.com", "authority": 84, "tier": "Regional Daily"},
            {"name": "Factly Telugu", "domain": "factly.in", "authority": 92, "tier": "Certified Fact-Checker"},
        ]
    },
    "bengali": {
        "name": "Bengali",
        "native": "বাংলা",
        "pattern": r'[\u0980-\u09FF]',
        "trusted_sources": [
            {"name": "Anandabazar Patrika", "domain": "anandabazar.com", "authority": 88, "tier": "Regional Premier Press"},
            {"name": "BBC Bangla", "domain": "bbc.com/bengali", "authority": 92, "tier": "Tier-2 Certified Broadcaster"},
            {"name": "Boom Bangla", "domain": "boomlive.in", "authority": 93, "tier": "Certified Fact-Checker"},
        ]
    },
}

# Common regional fact-checking keywords mapping
REGIONAL_TERMS = {
    "kannada": {
        "false": ["ಸುಳ್ಳು", "ನಕಲಿ", "ತಪ್ಪು", "ವದಂತಿ"],
        "true": ["ನಿಜ", "ಸತ್ಯ", "ಖಚಿತ", "ಸರಿ"],
        "warning": ["ಎಚ್ಚರಿಕೆ", "ಪರಿಶೀಲನೆ"]
    },
    "hindi": {
        "false": ["झूठ", "फर्जी", "गलत", "अफवाह", "दावा गलत"],
        "true": ["सच", "सही", "सत्य", "पुष्टि"],
        "warning": ["चेतावनी", "पड़ताल"]
    },
    "tamil": {
        "false": ["பொய்", "போலி", "வதந்தி"],
        "true": ["உண்மை", "சரி"],
        "warning": ["எச்சரிக்கை"]
    },
    "telugu": {
        "false": ["అబద్ధం", "నకిలీ", "వదంతులు"],
        "true": ["నిజం", "వాస్తవం"],
        "warning": ["హెచ్చరిక"]
    }
}


def detect_indian_language(text: str) -> Dict[str, Any]:
    """
    Detects if the text contains Indian language scripts.
    Returns language metadata while strictly preserving the original text.
    """
    if not text:
        return {"is_indian_language": False, "language_code": "en", "language_name": "English"}

    total_chars = len(text)
    script_counts = {}

    for lang_code, meta in SCRIPT_RANGES.items():
        matches = re.findall(meta["pattern"], text)
        if matches:
            script_counts[lang_code] = len(matches)

    if not script_counts:
        return {
            "is_indian_language": False,
            "language_code": "en",
            "language_name": "English",
            "native_name": "English",
            "regional_sources": [],
            "preserved_original": text,
        }

    detected_code = max(script_counts, key=script_counts.get)
    meta = SCRIPT_RANGES[detected_code]

    return {
        "is_indian_language": True,
        "language_code": detected_code,
        "language_name": meta["name"],
        "native_name": meta["native"],
        "regional_sources": meta["trusted_sources"],
        "preserved_original": text,
        "coverage_notice": f"Native {meta['name']} ({meta['native']}) detected. Prioritizing regional authoritative reporting.",
    }


def analyze_regional_keywords(text: str, language_code: str) -> Dict[str, Any]:
    """
    Searches for regional misinformation signals (e.g. 'ವದಂತಿ' in Kannada or 'फर्जी' in Hindi).
    """
    terms = REGIONAL_TERMS.get(language_code, {})
    refute_signals = []
    support_signals = []

    for word in terms.get("false", []):
        if word in text:
            refute_signals.append(word)

    for word in terms.get("true", []):
        if word in text:
            support_signals.append(word)

    return {
        "has_regional_refute_signal": len(refute_signals) > 0,
        "has_regional_support_signal": len(support_signals) > 0,
        "refute_words": refute_signals,
        "support_words": support_signals,
    }


if __name__ == "__main__":
    kannada_claim = "ಬೆಂಗಳೂರಿನಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿಗೆ ಕೊರತೆಯಾಗಿದೆ ಎಂದು ಸುಳ್ಳು ಸುದ್ದಿ ಹರಡಲಾಗಿದೆ"
    hindi_claim = "क्या सरकार सभी विद्यार्थियों को मुफ्त लैपटॉप दे रही है?"
    print("Kannada check:", detect_indian_language(kannada_claim)["language_name"])
    print("Hindi check:", detect_indian_language(hindi_claim)["language_name"])
