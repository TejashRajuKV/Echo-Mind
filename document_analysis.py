"""
document_analysis.py — Research Document & Official Notice Analysis Engine
==========================================================================
Extracts claims from documents, research papers, official notices, and reports,
chunking passages and linking each extracted assertion to its exact paragraph or passage.
"""

import re
from typing import List, Dict, Any, Optional


def chunk_document_passages(text: str, max_chunk_chars: int = 600) -> List[Dict[str, Any]]:
    """
    Chunks long documents into labeled passages, preserving paragraph numbers
    and approximate page numbers for precise citation tracing.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    # Split by double newline or explicit section breaks
    raw_paragraphs = re.split(r'\n\s*\n', clean_text)
    passages = []
    current_char_count = 0

    for idx, para in enumerate(raw_paragraphs, 1):
        para_clean = para.strip()
        if not para_clean:
            continue

        # Approximate 2,000 characters per standard document page
        estimated_page = (current_char_count // 2000) + 1
        current_char_count += len(para_clean)

        passages.append({
            "passage_id": f"passage_{idx}",
            "paragraph_num": idx,
            "estimated_page": estimated_page,
            "text": para_clean,
            "word_count": len(para_clean.split()),
        })

    return passages


def extract_claims_from_passages(passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identifies declarative factual assertions within passages that warrant fact-checking.
    Looks for numerical statistics, regulatory decrees, scientific assertions, and definitive statements.
    """
    extracted_claims = []
    claim_id = 1

    # Heuristic markers of verifiable claims
    claim_patterns = [
        r'\b(?:announced|declared|reported|discovered|confirmed|proved|banned|mandated|passed|decreed)\b',
        r'\b\d+(?:\.\d+)?%|\b\d+\s*(?:crore|lakh|million|billion|trillion|cases|deaths|rupees|dollars)\b',
        r'\b(?:according to|study shows|ministry stated|court ruled|who warned|icmr said)\b',
    ]

    for p in passages:
        # Split paragraph into sentences
        sentences = re.split(r'(?<=[.!?])\s+', p["text"])
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean.split()) < 5:
                continue

            # Check if sentence contains verifiable claim signals
            is_claim = any(re.search(pat, s_clean, re.IGNORECASE) for pat in claim_patterns)
            if is_claim or len(sentences) <= 2:  # In short notices, every sentence is a claim
                extracted_claims.append({
                    "claim_id": f"doc_claim_{claim_id}",
                    "claim_text": s_clean,
                    "source_passage_id": p["passage_id"],
                    "paragraph_num": p["paragraph_num"],
                    "estimated_page": p["estimated_page"],
                    "surrounding_context": p["text"][:280] + ("..." if len(p["text"]) > 280 else ""),
                })
                claim_id += 1
                if len(extracted_claims) >= 12:  # Limit per document analysis batch
                    break
        if len(extracted_claims) >= 12:
            break

    # If no pattern matches, fallback to first 3 significant sentences
    if not extracted_claims and passages:
        first_para = passages[0]["text"]
        first_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', first_para) if len(s.split()) >= 4]
        for idx, s in enumerate(first_sentences[:3], 1):
            extracted_claims.append({
                "claim_id": f"doc_claim_{idx}",
                "claim_text": s,
                "source_passage_id": passages[0]["passage_id"],
                "paragraph_num": 1,
                "estimated_page": 1,
                "surrounding_context": first_para[:250],
            })

    return extracted_claims


def analyze_document_content(
    document_text: str,
    document_title: str = "Submitted Document",
    verify_claims: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for Research Document & Official Notice Analysis:
    1. Chunks document into labeled passages and pages
    2. Extracts atomic verifiable claims
    3. Traces citations back to exact passages
    4. Optionally runs fast verification on top extracted claims
    """
    passages = chunk_document_passages(document_text)
    claims = extract_claims_from_passages(passages)

    verified_claims = []
    if verify_claims and claims:
        from analysis_engine import analyze_claim
        for c in claims[:4]:  # Verify top 4 claims for instant analysis
            res = analyze_claim(c["claim_text"], save_to_database=False)
            verified_claims.append({
                "claim_id": c["claim_id"],
                "claim_text": c["claim_text"],
                "paragraph_num": c["paragraph_num"],
                "estimated_page": c["estimated_page"],
                "surrounding_context": c["surrounding_context"],
                "verdict": res.get("classification", "Unknown"),
                "score": res.get("score", 50),
                "explanation": res.get("explanation", ""),
                "sources_count": len(res.get("evidence_sources", [])),
                "top_source": (res.get("evidence_sources") or [{}])[0].get("publisher", ""),
            })

    # Compute overall document integrity index
    scores = [vc["score"] for vc in verified_claims] if verified_claims else [50]
    avg_score = round(sum(scores) / len(scores), 1)

    return {
        "document_title": document_title,
        "total_passages": len(passages),
        "total_claims_extracted": len(claims),
        "total_claims_verified": len(verified_claims),
        "document_integrity_score": avg_score,
        "verified_claims": verified_claims,
        "passages_sample": passages[:3],
    }


if __name__ == "__main__":
    sample_notice = """
    GOVERNMENT OF KARNATAKA - DEPARTMENT OF HEALTH AND FAMILY WELFARE
    Official Press Release - Ref: HFW/2026/894
    
    The Department has announced that 15,000 community health workers have been deployed across all districts.
    A budget of 500 crore rupees was sanctioned for pediatric healthcare infrastructure.
    
    The Ministry confirmed that drinking boiled water and adhering to hygiene protocols prevents the spread of seasonal viral fevers.
    No emergency lockdown has been ordered for schools.
    """
    res = analyze_document_content(sample_notice, "Karnataka Health Circular", verify_claims=False)
    print(f"Extracted {res['total_claims_extracted']} claims from {res['total_passages']} passages.")
    for c in res["passages_sample"]:
        print("Passage:", c["passage_id"], "Page:", c["estimated_page"])
