"""
verification_engine.py — Multi-Source Verification and Conflict Detection
=========================================================================
Decomposes claims into atomic sub-claims, matches independent evidence,
detects consensus vs conflict across sources, weighs domain authority,
and computes a transparent, explainable multi-factor credibility score.
"""

import re
import math
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse


MULTI_LABEL_SUFFIXES = {
    "ac.in", "co.in", "com.au", "com.br", "com.cn", "com.sg", "co.nz",
    "co.uk", "gov.in", "net.au", "org.in", "org.uk",
}

PUBLISHER_ALIASES = {
    "the times of india": "times-group",
    "times of india": "times-group",
    "the economic times": "times-group",
    "economic times": "times-group",
}


def publisher_identity(source: dict) -> str:
    """Return a stable publisher key for source independence calculations."""
    cluster = str(source.get("cluster_id") or "").strip().casefold()
    if cluster and cluster != "standalone" and (
        source.get("is_syndicated") or source.get("is_echo_chamber") or cluster.startswith("wire:")
    ):
        return f"cluster:{cluster}"

    domain = str(source.get("domain") or "").strip().casefold().removeprefix("www.")
    if not domain:
        url = str(source.get("url") or source.get("link") or "")
        domain = (urlparse(url).hostname or "").casefold().removeprefix("www.")
    if domain.endswith(".indiatimes.com") or domain == "indiatimes.com":
        return "times-group"
    if domain:
        labels = domain.split(".")
        if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
            return ".".join(labels[-3:])
        return ".".join(labels[-2:]) if len(labels) >= 2 else domain

    publisher = re.sub(r"[^a-z0-9]+", " ", str(source.get("publisher") or "").casefold()).strip()
    return PUBLISHER_ALIASES.get(publisher, publisher or "unknown")


def decompose_claim(claim: str) -> List[Dict[str, Any]]:
    """
    Decompose a complex or compound claim into atomic, verifiable sub-claims.
    Splits along contrastive/coordinating conjunctions and punctuation clauses.
    """
    claim = claim.strip()
    if not claim:
        return []

    # Common compound splitters: "and also", "as well as", "while", "but", "however", "and"
    # We protect abbreviations like "U.S.", "Dr.", "etc."
    cleaned = claim
    patterns = [
        r'\s+(?:and\s+also|as\s+well\s+as|while\s+at\s+the\s+same\s+time)\s+',
        r'\s*;\s*',
        r'\s*,\s*(?:while|whereas|but|and)\s+',
        r'\s+(?:while|whereas|but)\s+',
        r'\s+(?:and)\s+(?=[A-Z0-9]|the\s+|it\s+|they\s+|he\s+|she\s+|this\s+|is\s+|was\s+|will\s+|has\s+|have\s+)',
    ]

    parts = [cleaned]
    for pat in patterns:
        new_parts = []
        for part in parts:
            splits = re.split(pat, part, flags=re.IGNORECASE)
            for s in splits:
                s_clean = s.strip()
                if len(s_clean.split()) >= 3:  # Only meaningful clauses with at least 3 words
                    new_parts.append(s_clean)
                elif new_parts:
                    # Append very short fragment back to the previous part
                    new_parts[-1] = f"{new_parts[-1]} {s_clean}".strip()
                else:
                    new_parts.append(s_clean)
        parts = new_parts

    # Fallback to full claim if no decomposition found or only trivial fragments
    if not parts or len(parts) == 1:
        return [{
            "id": "subclaim_1",
            "text": claim,
            "is_compound": False,
        }]

    subclaims = []
    for idx, part in enumerate(parts, 1):
        subclaims.append({
            "id": f"subclaim_{idx}",
            "text": part,
            "is_compound": True,
        })

    return subclaims


def associate_evidence_with_subclaim(subclaim_text: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find relevant evidence sources for a specific atomic sub-claim
    and evaluate stance relevance.
    """
    words = [w.lower() for w in re.findall(r'\b\w{3,}\b', subclaim_text)]
    stop_words = {"the", "and", "that", "this", "with", "from", "have", "been", "were", "will"}
    keywords = [w for w in words if w not in stop_words]

    matched = []
    for src in sources:
        searchable = f"{src.get('title','')} {src.get('excerpt','')} {src.get('textual_rating','')}".lower()
        match_count = sum(1 for kw in keywords if kw in searchable)
        if match_count > 0:
            relevance = min(1.0, match_count / max(1, len(keywords) * 0.5))
            item = dict(src)
            item["relevance_score"] = round(relevance, 2)
            matched.append(item)

    # Sort by relevance and authority
    matched.sort(key=lambda x: (x.get("relevance_score", 0), x.get("authority_score", 0)), reverse=True)
    return matched


def evaluate_conflict_and_consensus(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes multi-source agreement vs contradiction across independent sources.
    Calculates weighted consensus and detects controversy/conflict.
    """
    if not sources:
        return {
            "status": "Unverified / Insufficient Evidence",
            "conflict_detected": False,
            "consensus_direction": "unknown",
            "consensus_percentage": 0.0,
            "weighted_support": 0.0,
            "weighted_refute": 0.0,
            "supporting_sources_count": 0,
            "refuting_sources_count": 0,
            "neutral_sources_count": 0,
            "echo_chamber_detected": False,
            "independent_publisher_count": 0,
            "detail": "No external primary or secondary sources found to verify this statement.",
        }

    # Separate by stance and weight by domain authority (scale: 0.1 to 1.0)
    weighted_support = 0.0
    weighted_refute = 0.0
    weighted_neutral = 0.0

    support_publishers = set()
    refute_publishers = set()
    neutral_publishers = set()
    clusters_seen = set()
    echo_count = 0

    for s in sources:
        auth = s.get("authority_score", 50)
        # Authority factor 0.3 to 1.0
        weight = max(0.3, auth / 100.0)
        stance = s.get("stance", "neutral")
        cid = str(s.get("cluster_id") or "standalone").strip().casefold()
        pub = publisher_identity(s)

        if s.get("is_echo_chamber", False):
            echo_count += 1
            # Diminish weight of syndicated copy to prevent echo chambers from dominating
            weight *= 0.5

        clusters_seen.add(cid)

        if stance == "supports":
            weighted_support += weight
            support_publishers.add(pub)
        elif stance == "refutes":
            weighted_refute += weight
            refute_publishers.add(pub)
        else:
            weighted_neutral += weight
            neutral_publishers.add(pub)

    total_weighted = weighted_support + weighted_refute + (weighted_neutral * 0.2)
    conflict_detected = False
    status = "Unverified"
    consensus_dir = "neutral"
    consensus_pct = 0.0

    # Directional consensus requires at least two independent publishers taking
    # the same non-neutral position. Neutral topical coverage cannot "vote" a
    # claim true or false, and multiple URLs from one domain remain one publisher.
    independent_count = len(support_publishers | refute_publishers | neutral_publishers)
    directional_publishers = len(support_publishers | refute_publishers)
    if independent_count < 2 or directional_publishers < 2:
        return {
            "status": "Unverified / Insufficient Independent Evidence",
            "conflict_detected": False,
            "consensus_direction": "unknown",
            "consensus_percentage": 0.0,
            "weighted_support": round(weighted_support, 2),
            "weighted_refute": round(weighted_refute, 2),
            "supporting_sources_count": len(support_publishers),
            "refuting_sources_count": len(refute_publishers),
            "neutral_sources_count": len(neutral_publishers),
            "echo_chamber_detected": echo_count > 0,
            "independent_publisher_count": independent_count,
            "detail": "Fewer than two independent publishers with directional evidence were found. Treat this result as unverified, not as consensus.",
        }

    # Evaluate conflict threshold:
    # If both support and refute have substantial weight
    if weighted_support > 0 and weighted_refute > 0:
        ratio = min(weighted_support, weighted_refute) / max(weighted_support, weighted_refute)
        if ratio >= 0.25:  # Significant disagreement
            conflict_detected = True
            status = "Direct Conflict / Contested Claim"
            consensus_dir = "disputed"
            consensus_pct = round((1.0 - ratio) * 100, 1)
            detail = (
                f"Conflicting evidence detected across reporting outlets. "
                f"{len(support_publishers)} source(s) support while {len(refute_publishers)} source(s) refute or contradict the assertion."
            )
        elif weighted_refute > weighted_support:
            status = "Strong Consensus (Refuted)"
            consensus_dir = "refuted"
            consensus_pct = round((weighted_refute / total_weighted) * 100, 1)
            detail = f"Dominant consensus across authoritative sources refutes this claim ({len(refute_publishers)} refuting vs {len(support_publishers)} supporting)."
        else:
            status = "Strong Consensus (Supported)"
            consensus_dir = "supported"
            consensus_pct = round((weighted_support / total_weighted) * 100, 1)
            detail = f"Broad consensus across authoritative sources supports this claim ({len(support_publishers)} supporting vs {len(refute_publishers)} dissenting)."
    elif weighted_refute > 0:
        status = "Strong Consensus (Refuted)"
        consensus_dir = "refuted"
        consensus_pct = 100.0
        detail = f"All {len(refute_publishers)} identified verifying source(s) mark this assertion as false, debunked, or incorrect."
    elif weighted_support > 0:
        status = "Strong Consensus (Supported)"
        consensus_dir = "supported"
        consensus_pct = 100.0
        detail = f"All {len(support_publishers)} identified verifying source(s) confirm the veracity of this statement."
    else:
        status = "Contextual / Neutral Evidence"
        consensus_dir = "neutral"
        consensus_pct = 50.0
        detail = "Available reporting provides topical context but neither conclusively validates nor refutes the claim."

    return {
        "status": status,
        "conflict_detected": conflict_detected,
        "consensus_direction": consensus_dir,
        "consensus_percentage": consensus_pct,
        "weighted_support": round(weighted_support, 2),
        "weighted_refute": round(weighted_refute, 2),
        "supporting_sources_count": len(support_publishers),
        "refuting_sources_count": len(refute_publishers),
        "neutral_sources_count": len(neutral_publishers),
        "echo_chamber_detected": echo_count > 0,
        "independent_publisher_count": len(support_publishers | refute_publishers | neutral_publishers),
        "detail": detail,
    }


def compute_credibility_score(sources: List[Dict[str, Any]], consensus: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes an explainable, multi-factor credibility score (0-100) based on:
    1. Source Convergence: Stance agreement ratio across independent sources
    2. Evidence Authority: Average domain authority of supporting vs refuting sources
    3. Publisher Independence: Breadth of independent clusters without echo amplification
    """
    if not sources:
        return {
            "score": 50,
            "verdict": "Unverified",
            "confidence": "Low",
            "breakdown": {
                "source_convergence_score": 50,
                "evidence_authority_score": 50,
                "publisher_independence_score": 50,
            },
            "formula_explanation": "Default unverified score: No primary or secondary citations were found.",
        }

    # 1. Authority factor (0-100)
    top_authorities = [s.get("authority_score", 50) for s in sources]
    avg_authority = sum(top_authorities) / len(top_authorities)

    # 2. Convergence factor (0-100)
    w_sup = consensus.get("weighted_support", 0.0)
    w_ref = consensus.get("weighted_refute", 0.0)
    total_w = w_sup + w_ref

    if total_w > 0:
        net_support_ratio = (w_sup - w_ref) / total_w  # -1.0 (fully refuted) to +1.0 (fully supported)
        convergence_score = round(((net_support_ratio + 1.0) / 2.0) * 100, 1)
    else:
        convergence_score = 50.0

    # 3. Independence factor (0-100)
    indep_count = consensus.get("independent_publisher_count", 1)
    independence_score = min(100, 40 + (indep_count * 15))
    if consensus.get("echo_chamber_detected"):
        independence_score = max(30, independence_score - 15)

    # Weighted composite score
    # Convergence carries 50%, Authority carries 35%, Independence carries 15%
    composite = (convergence_score * 0.50) + (avg_authority * 0.35) + (independence_score * 0.15)
    final_score = int(max(5, min(98, round(composite))))

    # Classification verdict
    if consensus.get("conflict_detected"):
        verdict = "Suspicious"
        confidence = "Disputed"
    elif w_ref > w_sup and final_score <= 40:
        verdict = "False"
        confidence = "High" if avg_authority >= 80 else "Moderate"
    elif w_sup > w_ref and final_score >= 65:
        verdict = "Trustworthy"
        confidence = "High" if avg_authority >= 80 else "Moderate"
    else:
        verdict = "Suspicious"
        confidence = "Moderate"

    return {
        "score": final_score,
        "verdict": verdict,
        "confidence": confidence,
        "breakdown": {
            "source_convergence_score": round(convergence_score, 1),
            "evidence_authority_score": round(avg_authority, 1),
            "publisher_independence_score": round(independence_score, 1),
        },
        "formula_explanation": (
            f"Calculated from Source Convergence ({convergence_score:.0f}%), "
            f"Evidence Authority ({avg_authority:.0f}%), and Publisher Diversity ({independence_score:.0f}%)."
        ),
    }


def verify_claim_multisource(claim: str, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main verification pipeline:
    1. Decompose claim into sub-claims
    2. Correlate sub-claims with retrieved evidence
    3. Analyze conflict & consensus
    4. Compute multi-factor credibility score
    """
    subclaims = decompose_claim(str(claim or ""))
    evidence_data = evidence_data if isinstance(evidence_data, dict) else {}
    raw_sources = evidence_data.get("sources", [])
    sources = [source for source in raw_sources if isinstance(source, dict)] if isinstance(raw_sources, list) else []

    # Sub-claim analysis
    analyzed_subclaims = []
    for sc in subclaims:
        sc_sources = associate_evidence_with_subclaim(sc["text"], sources)
        sc_consensus = evaluate_conflict_and_consensus(sc_sources)
        analyzed_subclaims.append({
            "id": sc["id"],
            "text": sc["text"],
            "sources_count": len(sc_sources),
            "status": sc_consensus["status"],
            "consensus_direction": sc_consensus["consensus_direction"],
            "top_sources": [
                {
                    "publisher": s.get("publisher", ""),
                    "domain": s.get("domain", ""),
                    "stance": s.get("stance", ""),
                    "authority_score": s.get("authority_score", 50),
                    "url": s.get("url", ""),
                }
                for s in sc_sources[:3]
            ],
        })

    # Overall consensus and score
    overall_consensus = evaluate_conflict_and_consensus(sources)
    score_analysis = compute_credibility_score(sources, overall_consensus)

    return {
        "subclaims": analyzed_subclaims,
        "is_compound_claim": len(subclaims) > 1,
        "consensus": overall_consensus,
        "credibility": score_analysis,
    }


if __name__ == "__main__":
    claim_test = "WHO declared monkeypox a public health emergency and vaccines will be mandatory across all schools"
    print("Decomposing test claim...")
    parts = decompose_claim(claim_test)
    for p in parts:
        print(" -", p)
